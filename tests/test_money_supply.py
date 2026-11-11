from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from backend import database
from backend.money_supply import calc, sources
from backend.money_supply import service as module
from backend.money_supply.service import MoneySupplyService
from backend.money_supply.sources import Fetched, SourceError, parse_last_updated, parse_next_release, parse_observations
from backend.routers import money_supply as router_module

TODAY = date(2026, 11, 11)
NOW = datetime(2026, 11, 11, 15, 0, tzinfo=timezone.utc)
SECRET = "SECRETKEY1234"


def months(start: str, values: list[float]) -> list[tuple[str, float]]:
    return [(calc.shift_month(start, i), v) for i, v in enumerate(values)]


def fred_reply(request):
    path = request.url.path
    if path.endswith("/series/observations"):
        return httpx.Response(200, json={"observations": [
            {"date": "2026-08-01", "value": "23300.9"},
            {"date": "2026-07-01", "value": "."},
            {"date": "2026-09-01", "value": "23413.9"},
        ]})
    if path.endswith("/series"):
        return httpx.Response(200, json={"seriess": [{"last_updated": "2026-10-27 12:01:34-05"}]})
    if path.endswith("/release/dates"):
        return httpx.Response(200, json={"release_dates": [{"date": "2026-12-22"}, {"date": "2026-11-24"}]})
    return httpx.Response(404)


# ── Parsing ──────────────────────────────────────────────────────────────────


def test_missing_values_are_dropped_and_months_sorted():
    rows = parse_observations({"observations": [{"date": "1959-02-01", "value": "287.7"}, {"date": "1959-01-01", "value": "."}, {"date": "1958-12-01", "value": "286.6"}]})
    assert rows == [("1958-12-01", 286.6), ("1959-02-01", 287.7)]


def test_last_updated_with_an_hour_only_offset():
    assert parse_last_updated({"seriess": [{"last_updated": "2026-10-27 12:01:34-05"}]}) == datetime(2026, 10, 27, 17, 1, 34, tzinfo=timezone.utc)


def test_unreadable_last_updated_is_left_out():
    assert parse_last_updated({"seriess": [{"last_updated": "soon"}]}) is None


def test_next_release_is_the_first_from_today():
    payload = {"release_dates": [{"date": "2026-12-22"}, {"date": "2026-10-27"}, {"date": "2026-11-24"}]}
    assert parse_next_release(payload, TODAY) == date(2026, 11, 24)
    assert parse_next_release({"release_dates": []}, TODAY) is None


async def test_fetch_reads_all_three_endpoints():
    async with httpx.AsyncClient(transport=httpx.MockTransport(fred_reply)) as client:
        fetched = await sources.fetch_m2(client, "k", TODAY)
    assert fetched.observations == [("2026-08-01", 23300.9), ("2026-09-01", 23413.9)]
    assert fetched.last_updated == datetime(2026, 10, 27, 17, 1, 34, tzinfo=timezone.utc)
    assert fetched.next_release == date(2026, 11, 24)


async def test_a_failed_release_calendar_only_drops_the_next_release():
    def reply(request):
        return httpx.Response(500) if request.url.path.endswith("/release/dates") else fred_reply(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
        fetched = await sources.fetch_m2(client, "k", TODAY)
    assert fetched.next_release is None and len(fetched.observations) == 2


async def test_network_errors_never_carry_the_key():
    def fail(request):
        raise httpx.ConnectError(f"failed {request.url}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(SourceError) as err:
            await sources.fetch_m2(client, SECRET, TODAY)
    assert SECRET not in str(err.value) and "stlouisfed" not in str(err.value)
    assert "ConnectError" in str(err.value)


async def test_http_errors_show_the_status():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(400))) as client:
        with pytest.raises(SourceError) as err:
            await sources.fetch_m2(client, SECRET, TODAY)
    assert str(err.value) == "FRED returned HTTP 400"


async def test_unexpected_reply_is_an_error():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"oops": 1}))) as client:
        with pytest.raises(SourceError, match="unexpected"):
            await sources.fetch_m2(client, "k", TODAY)


# ── Calculations ─────────────────────────────────────────────────────────────


def test_shift_month_crosses_years():
    assert calc.shift_month("2026-01-01", -1) == "2025-12-01"
    assert calc.shift_month("2026-03-01", -12) == "2025-03-01"
    assert calc.shift_month("2025-12-01", 1) == "2026-01-01"


def test_first_year_has_no_growth():
    rows = calc.with_growth(months("1959-01-01", [100 + i for i in range(13)]))
    assert all(r["yoy_pct"] is None for r in rows[:12])
    assert rows[12]["month"] == "1960-01-01"
    assert rows[12]["yoy_pct"] == pytest.approx(12.0)


def test_contraction_is_negative():
    rows = calc.with_growth(months("2022-01-01", [200] + [199] * 11 + [190]))
    assert rows[-1]["yoy_pct"] == pytest.approx(-5.0)


def test_gap_a_year_earlier_means_no_growth():
    rows = calc.with_growth([("2025-08-01", 100.0), ("2026-09-01", 110.0)])
    assert rows[-1]["yoy_pct"] is None


def test_latest_reading():
    obs = months("2025-09-01", [20000] + [20500] * 11 + [21000])
    latest = calc.latest_reading(obs)
    assert latest["month"] == "2026-09-01" and latest["value"] == 21000
    assert latest["mom_change"] == 500 and latest["mom_pct"] == pytest.approx(500 / 20500 * 100)
    assert latest["yoy_change"] == 1000 and latest["yoy_pct"] == pytest.approx(5.0)


def test_latest_reading_without_history():
    assert calc.latest_reading([]) is None
    latest = calc.latest_reading([("2026-09-01", 1.0)])
    assert latest["mom_change"] is None and latest["yoy_pct"] is None


# ── Service ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def world(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    state = SimpleNamespace(key="k1", calls=[], fail=None, fetched=Fetched(months("2025-09-01", [20000 + i * 10 for i in range(13)]), datetime(2026, 10, 27, 17, tzinfo=timezone.utc), date(2026, 11, 24)))
    monkeypatch.setattr(module, "get_calendar_settings", lambda: SimpleNamespace(fred_api_key=state.key))

    async def fetch(client, key, today):
        state.calls.append(key)
        if state.fail:
            raise SourceError(state.fail)
        return state.fetched

    monkeypatch.setattr(sources, "fetch_m2", fetch)
    state.service = MoneySupplyService()
    yield state
    await database._engine.dispose()


async def test_refresh_saves_and_reports_ok(world):
    await world.service.refresh_due(NOW)
    state = await world.service.state(NOW)
    assert state["status"] == "ok"
    assert len(state["observations"]) == 13 and state["observations"][-1]["yoy_pct"] == pytest.approx(0.6)
    assert state["latest"]["month"] == "2026-09-01"
    assert state["next_release"] == "2026-11-24"
    assert state["last_updated"].startswith("2026-10-27T17:00")
    assert state["fetched_at"].startswith("2026-11-11T15:00")


async def test_refresh_waits_six_hours(world):
    await world.service.refresh_due(NOW)
    await world.service.refresh_due(NOW + timedelta(hours=5, minutes=59))
    assert len(world.calls) == 1
    await world.service.refresh_due(NOW + timedelta(hours=6))
    assert len(world.calls) == 2


async def test_failure_keeps_saved_data_and_retries_within_an_hour(world):
    await world.service.refresh_due(NOW)
    world.fail = "FRED returned HTTP 500"
    later = NOW + timedelta(hours=6)
    await world.service.refresh_due(later)
    state = await world.service.state(later)
    assert state["status"] == "error" and state["error"] == "FRED returned HTTP 500"
    assert len(state["observations"]) == 13
    assert state["fetched_at"].startswith("2026-11-11T15:00")
    await world.service.refresh_due(later + timedelta(minutes=59))
    assert len(world.calls) == 2
    world.fail = None
    await world.service.refresh_due(later + timedelta(hours=1))
    assert len(world.calls) == 3
    assert (await world.service.state(later))["status"] == "ok"


async def test_no_key_fetches_nothing(world):
    world.key = ""
    await world.service.refresh_due(NOW)
    state = await world.service.state(NOW)
    assert world.calls == [] and state["status"] == "no_key" and state["observations"] == []


async def test_adding_or_changing_the_key_refreshes_right_away(world):
    world.key = ""
    await world.service.refresh_due(NOW)
    world.key = "k1"
    await world.service.refresh_due(NOW + timedelta(minutes=1))
    world.key = "k2"
    await world.service.refresh_due(NOW + timedelta(minutes=2))
    assert world.calls == ["k1", "k2"]


async def test_before_the_first_fetch_it_is_loading(world):
    assert (await world.service.state(NOW))["status"] == "loading"


async def test_saved_data_survives_a_restart(world):
    await world.service.refresh_due(NOW)
    world.fail = "FRED couldn't be reached (ConnectError)"
    restarted = MoneySupplyService()
    await restarted.refresh_due(NOW)
    state = await restarted.state(NOW)
    assert len(state["observations"]) == 13 and state["latest"] is not None


async def test_a_passed_release_date_is_dropped(world):
    await world.service.refresh_due(NOW)
    assert (await world.service.state(NOW + timedelta(days=14)))["next_release"] is None


async def test_api_never_returns_the_key(world, monkeypatch):
    world.key = SECRET
    world.fail = "FRED returned HTTP 400"
    await world.service.refresh_due(NOW)
    monkeypatch.setattr(router_module, "money_supply_service", world.service)
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/money-supply")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/money-supply")
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert SECRET not in response.text
