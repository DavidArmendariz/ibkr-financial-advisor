import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend import database
from backend.database import SignalEvent
from backend.routers import signals as signals_router
from backend.signals.rules import EMA_CROSS, VOLUME_SPIKE, VWAP_CROSS
from backend.signals.service import SignalService

START = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)


def event(row_id, minute, signal_type=VOLUME_SPIKE):
    payload = {"category": "volume", "indicators": {}, "bars": [{"close": 1}], "llm": {"action": "skip"}, "notified": False}
    return SignalEvent(
        id=row_id, time=START + timedelta(minutes=minute), signal_type=signal_type, symbol="SOXL", price=100.0, payload=json.dumps(payload)
    )


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()

    async def seed(rows):
        async with database.AsyncSessionLocal() as session:
            session.add_all(rows)
            await session.commit()

    yield seed
    await database._engine.dispose()


async def walk(service, limit, signal_type=None):
    pages, before = [], None
    while True:
        page = await service.history_page(limit, signal_type, before)
        pages.append([s["id"] for s in page["signals"]])
        before = page["next_cursor"]
        if before is None:
            return pages


async def test_newest_first_without_bars(db):
    await db([event("a", 0), event("b", 2), event("c", 1)])
    page = await SignalService().history_page(10)
    assert [s["id"] for s in page["signals"]] == ["b", "c", "a"]
    assert page["next_cursor"] is None
    assert "bars" not in page["signals"][0]
    assert page["signals"][0]["time"].endswith("+00:00")


async def test_a_page_boundary_inside_one_bar_skips_and_repeats_nothing(db):
    await db([event("a", 1, VOLUME_SPIKE), event("b", 1, EMA_CROSS), event("c", 1, VWAP_CROSS), event("d", 0)])
    assert await walk(SignalService(), 2) == [["c", "b"], ["a", "d"]]


async def test_no_cursor_when_the_page_is_exactly_full(db):
    await db([event("a", 0), event("b", 1)])
    assert (await SignalService().history_page(2))["next_cursor"] is None


async def test_filter_applies_across_pages(db):
    await db([event(f"e{i}", i, EMA_CROSS) for i in range(3)] + [event(f"v{i}", i + 10) for i in range(3)])
    assert await walk(SignalService(), 2, EMA_CROSS) == [["e2", "e1"], ["e0"]]


async def test_a_new_signal_does_not_shift_older_pages(db):
    await db([event("a", 0), event("b", 1), event("c", 2)])
    service = SignalService()
    first = await service.history_page(2)
    await db([event("new", 3)])
    older = await service.history_page(2, None, first["next_cursor"])
    assert [s["id"] for s in older["signals"]] == ["a"]


async def test_endpoint_rejects_unknown_type_and_bad_cursor(db):
    with pytest.raises(HTTPException) as err:
        await signals_router.get_history(100, "NOPE", None)
    assert err.value.status_code == 422
    with pytest.raises(HTTPException) as err:
        await signals_router.get_history(100, None, "garbage")
    assert err.value.status_code == 422


async def test_endpoint_reads_saved_signals(db):
    await db([event("a", 0, EMA_CROSS)])
    page = await signals_router.get_history(100, EMA_CROSS, None)
    assert [s["id"] for s in page["signals"]] == ["a"]
