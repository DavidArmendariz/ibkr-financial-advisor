import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend import database
from backend.database import OutcomeBaseline, SignalEvent, SignalOutcome
from backend.routers import signals as signals_router
from backend.services import ibkr_service
from backend.signals import outcomes, service as signal_module
from backend.signals.rules import EMA_CROSS, VOLUME_SPIKE
from backend.signals.service import SignalService
from backend.signals.sessions import ET

OPEN = datetime(2026, 10, 6, 9, 30, tzinfo=ET)
CLOSE = datetime(2026, 10, 6, 16, 0, tzinfo=ET)
AFTER = datetime(2026, 10, 7, 12, 0, tzinfo=ET)
SIGNAL = OPEN + timedelta(minutes=60)


def bar(when, close, high=None, low=None):
    return {"time": int(when.timestamp()) - 60, "open": close, "high": high or close, "low": low or close, "close": close, "volume": 1}


def session(start=OPEN, end=CLOSE, price=lambda i: 100.0):
    count = int((end - start).total_seconds() // 60)
    return [bar(start + timedelta(minutes=i + 1), price(i)) for i in range(count)]


# ── Figures ──────────────────────────────────────────────────────────────────


def test_moves_are_measured_from_the_signal_bar():
    bars = session(price=lambda i: 100.0 + max(0, i - 59))
    figures = outcomes.measure(bars, SIGNAL, CLOSE)
    assert figures["move_5m"] == pytest.approx(5.0)
    assert figures["move_15m"] == pytest.approx(15.0)
    assert figures["move_30m"] == pytest.approx(30.0)
    assert figures["max_up"] == pytest.approx(30.0)
    assert figures["max_down"] == 0.0


def test_largest_moves_use_highs_and_lows_inside_the_window():
    bars = [
        bar(SIGNAL, 100),
        bar(SIGNAL + timedelta(minutes=10), 100, high=103, low=98),
        bar(SIGNAL + timedelta(minutes=30), 100),
        bar(SIGNAL + timedelta(minutes=31), 100, high=120, low=80),
    ]
    figures = outcomes.measure(bars, SIGNAL, CLOSE)
    assert figures["max_up"] == pytest.approx(3.0)
    assert figures["max_down"] == pytest.approx(-2.0)


def test_a_late_signal_keeps_only_what_fits_before_the_close():
    late = CLOSE - timedelta(minutes=20)
    figures = outcomes.measure(session(price=lambda i: 100.0 + i), late, CLOSE)
    assert figures["move_5m"] is not None and figures["move_15m"] is not None
    assert figures["move_30m"] is None
    assert figures["max_up"] == pytest.approx((489.0 / 469.0 - 1) * 100)


def test_early_close_is_the_limit():
    close = OPEN.replace(hour=13, minute=0)
    late = close - timedelta(minutes=10)
    figures = outcomes.measure(session(end=close), late, close)
    assert figures["move_5m"] is not None
    assert figures["move_15m"] is None and figures["move_30m"] is None


def test_no_bar_at_the_signal_means_no_figures():
    assert outcomes.measure(session(), SIGNAL + timedelta(seconds=30), CLOSE) is None


def test_baseline_covers_every_minute_that_fits():
    series = outcomes.day_baseline(session(), CLOSE, ET)
    assert len(series["move_5m"]) == 385
    assert len(series["move_30m"]) == 360
    assert len(series["max_up"]) == 389


def test_summary_counts_each_horizon_separately():
    rows = [{"move_5m": 1.0, "move_15m": None}, {"move_5m": -2.0, "move_15m": 3.0}, {"move_5m": 4.0}]
    summary = outcomes.summarize(outcomes.collect(rows))
    five = summary["horizons"]["5m"]
    assert five["count"] == 3 and five["average"] == pytest.approx(1.0) and five["median"] == 1.0
    assert five["up_share"] == pytest.approx(2 / 3) and five["small_sample"] is True
    assert summary["horizons"]["15m"]["count"] == 1
    assert summary["horizons"]["30m"] == {"count": 0, "average": None, "median": None, "up_share": None, "small_sample": True}


def test_thirty_signals_is_no_longer_a_small_sample():
    assert outcomes.summarize({"move_5m": [1.0] * 30})["horizons"]["5m"]["small_sample"] is False


# ── Background pass ──────────────────────────────────────────────────────────


def event(row_id, when, signal_type=VOLUME_SPIKE):
    payload = {"category": "volume", "indicators": {}, "bars": [], "llm": {"action": "skip"}, "notified": False}
    return SignalEvent(id=row_id, time=when.astimezone(timezone.utc), signal_type=signal_type, symbol="SOXL", price=999.0, payload=json.dumps(payload))


@pytest.fixture
async def world(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    state = SimpleNamespace(connected=True, requests=[], replies=[], bars=session())

    async def seed(*rows):
        async with database.AsyncSessionLocal() as s:
            s.add_all(rows)
            await s.commit()

    async def fake_bars(*args, **kwargs):
        state.requests.append((args, kwargs))
        return state.replies.pop(0) if state.replies else state.bars

    def no_provider(*args):
        raise AssertionError("a provider was called")

    state.seed = seed
    monkeypatch.setattr(ibkr_service.ibkr, "isConnected", lambda: state.connected)
    monkeypatch.setattr(ibkr_service, "get_historical_bars", fake_bars)
    monkeypatch.setattr(signal_module, "resolve_provider", no_provider)
    state.service = SignalService()
    monkeypatch.setattr(signals_router, "signal_service", state.service)
    yield state
    await database._engine.dispose()


async def saved(signal_id="s1"):
    async with database.AsyncSessionLocal() as s:
        return await s.get(SignalOutcome, signal_id)


async def test_a_pass_saves_figures_and_a_baseline(world):
    await world.seed(event("s1", SIGNAL))
    await world.service.measure_outcomes(AFTER)
    row = await saved()
    assert row.status == "measured" and row.move_5m == 0.0
    assert world.requests[0][0][4] is True
    async with database.AsyncSessionLocal() as s:
        assert await s.get(OutcomeBaseline, "2026-10-06")


async def test_a_signal_waits_until_its_window_has_passed(world):
    await world.seed(event("s1", SIGNAL))
    await world.service.measure_outcomes(SIGNAL + timedelta(minutes=30))
    assert world.requests == [] and await saved() is None
    await world.service.measure_outcomes(SIGNAL + timedelta(minutes=31))
    assert (await saved()).status == "measured"


async def test_saved_figures_are_not_requested_again(world):
    await world.seed(event("s1", SIGNAL))
    await world.service.measure_outcomes(AFTER)
    await world.service.measure_outcomes(AFTER)
    assert len(world.requests) == 1


async def test_a_session_in_progress_gets_its_baseline_once_it_ends(world):
    await world.seed(event("s1", SIGNAL))
    world.bars = session(end=SIGNAL + timedelta(minutes=32))
    await world.service.measure_outcomes(SIGNAL + timedelta(minutes=32))
    assert (await saved()).move_30m is not None
    async with database.AsyncSessionLocal() as s:
        assert await s.get(OutcomeBaseline, "2026-10-06") is None
    world.bars = session()
    await world.service.measure_outcomes(AFTER)
    assert len(world.requests) == 2
    async with database.AsyncSessionLocal() as s:
        assert await s.get(OutcomeBaseline, "2026-10-06")


async def test_one_day_per_pass_newest_first(world):
    await world.seed(event("old", SIGNAL - timedelta(days=1)), event("new", SIGNAL))
    world.bars = session()
    await world.service.measure_outcomes(AFTER)
    assert len(world.requests) == 1
    assert (await saved("new")) is not None and (await saved("old")) is None


async def test_disconnected_pauses_without_marking_anything(world):
    await world.seed(event("s1", SIGNAL))
    world.connected = False
    await world.service.measure_outcomes(AFTER)
    assert world.requests == [] and await saved() is None


async def test_a_failed_request_leaves_the_signal_pending(world):
    await world.seed(event("s1", SIGNAL))
    world.bars = []
    await world.service.measure_outcomes(AFTER)
    assert len(world.requests) == 2 and await saved() is None


async def test_a_day_is_gone_only_if_ibkr_is_serving_bars(world):
    await world.seed(event("s1", SIGNAL))
    world.replies = [[], session()]
    await world.service.measure_outcomes(AFTER)
    assert (await saved()).status == "not_available"
    await world.service.measure_outcomes(AFTER)
    assert len(world.requests) == 2


async def test_no_bar_at_the_signal_is_not_available(world):
    await world.seed(event("s1", SIGNAL + timedelta(seconds=30)))
    await world.service.measure_outcomes(AFTER)
    assert (await saved()).status == "not_available"


async def test_a_pass_never_changes_the_signal_record(world):
    await world.seed(event("s1", SIGNAL))
    async with database.AsyncSessionLocal() as s:
        before = (await s.get(SignalEvent, "s1")).model_dump()
    await world.service.measure_outcomes(AFTER)
    async with database.AsyncSessionLocal() as s:
        assert (await s.get(SignalEvent, "s1")).model_dump() == before


def test_outcomes_contain_no_order_calls():
    for module in (outcomes, signal_module):
        source = open(module.__file__).read()
        assert "placeOrder" not in source and "cancelOrder" not in source


# ── API ──────────────────────────────────────────────────────────────────────


async def test_results_per_trigger_with_baseline(world):
    await world.seed(event("a", SIGNAL), event("b", SIGNAL + timedelta(minutes=5)), event("c", SIGNAL, EMA_CROSS))
    await world.service.measure_outcomes(AFTER)
    results = await signals_router.get_outcomes()
    assert [t["signal_type"] for t in results["triggers"]] == [VOLUME_SPIKE, EMA_CROSS]
    assert results["triggers"][0]["horizons"]["5m"]["count"] == 2
    assert results["baseline"]["horizons"]["5m"]["count"] == 385
    assert results["baseline_days"] == 1 and results["pending"] == 0 and results["min_sample"] == 30


async def test_results_with_nothing_measured(world):
    await world.seed(event("s1", SIGNAL))
    results = await signals_router.get_outcomes()
    assert results["triggers"] == [] and results["baseline"] is None and results["pending"] == 1


async def test_not_available_is_left_out_of_results(world):
    await world.seed(event("s1", SIGNAL), event("s2", SIGNAL + timedelta(seconds=30)))
    await world.service.measure_outcomes(AFTER)
    results = await signals_router.get_outcomes()
    assert results["triggers"][0]["horizons"]["5m"]["count"] == 1 and results["pending"] == 0


async def test_history_records_carry_the_outcome(world):
    await world.seed(event("s1", SIGNAL), event("s2", SIGNAL + timedelta(days=3)))
    await world.service.measure_outcomes(AFTER)
    signals = {s["id"]: s for s in (await world.service.history_page(10))["signals"]}
    assert signals["s1"]["outcome"]["status"] == "measured"
    assert signals["s2"]["outcome"] is None
