import asyncio
import inspect
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend import database
from backend.database import SignalEvent
from backend.routers import signals as signals_router
from backend.services import ibkr_service
from backend.signals import analysis, service as signal_module
from backend.signals.analysis import AnalysisError
from backend.signals.rules import EMA_CROSS, VOLUME_SPIKE, VWAP_BAND_ABOVE, VWAP_BAND_BELOW, VWAP_CROSS
from backend.signals.service import SignalService

SIGNAL_TIME = datetime(2026, 10, 28, 14, 30, tzinfo=timezone.utc)  # 10:30 ET
CLOSE_TIME = datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc)  # 16:00 ET
T0 = SIGNAL_TIME.timestamp()
PRE_REPLY = {"action": "take", "confidence": 0.7, "case_for": "Trend", "risks": "Chop", "invalidation": "Below VWAP"}
POST_REPLY = {"verdict": "good", "explanation": "It held."}


def bar(offset_minutes, close, high=None, low=None):
    return {
        "time": T0 + offset_minutes * 60,
        "open": close,
        "high": high if high is not None else close,
        "low": low if low is not None else close,
        "close": close,
        "volume": 100.0,
    }


def signal(signal_type=EMA_CROSS):
    return {
        "id": "s1",
        "time": SIGNAL_TIME.isoformat(),
        "symbol": "SOXL",
        "signal_type": signal_type,
        "category": "technical",
        "price": 100.0,
        "indicators": {"vwap": 99.0},
        "ema_periods": [9, 21],
        "bars": [{"close": 100.0}],
        "llm": {"action": "unfiltered"},
        "notified": True,
    }


class FakeProvider:
    name, model = "fake", "fake-model"

    def __init__(self, reply=None, delay=0.0, error=None):
        self.reply, self.delay, self.error = reply, delay, error
        self.calls = []

    async def complete(self, system, user, timeout, max_tokens=256, schema=None):
        self.calls.append(json.loads(user))
        self.max_tokens, self.schema = max_tokens, schema
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.reply


def test_the_bar_closing_at_the_signal_is_known_and_the_next_is_not():
    bars = [bar(-2, 99), bar(-1, 100), bar(0, 101)]
    assert [b["close"] for b in analysis.bars_known_at(bars, SIGNAL_TIME)] == [99, 100]
    assert [b["close"] for b in analysis.bars_after(bars, SIGNAL_TIME, CLOSE_TIME)] == [101]


def test_after_hours_bars_are_not_outcomes():
    bars = [bar(0, 101), bar(329, 102), bar(330, 500)]
    assert [b["close"] for b in analysis.bars_after(bars, SIGNAL_TIME, CLOSE_TIME)] == [101, 102]


def test_outcome_figures():
    later = [bar(i, 100 + i, high=100 + i + 0.5, low=100 + i - 2) for i in range(1, 70)]
    figures = analysis.outcomes(later, 100.0, SIGNAL_TIME, CLOSE_TIME)
    assert figures["return_pct"]["15m"] == pytest.approx(14)  # bar closing at +15 opened at +14
    assert figures["return_pct"]["30m"] == pytest.approx(29)
    assert figures["return_pct"]["60m"] == pytest.approx(59)
    assert figures["return_pct"]["close"] == pytest.approx(69)
    assert figures["largest_gain_pct"] == pytest.approx(69.5)
    assert figures["largest_loss_pct"] == pytest.approx(-1)
    assert figures["returned_to_start"] is True


def test_a_horizon_after_the_close_is_not_available():
    close = SIGNAL_TIME + timedelta(minutes=20)
    figures = analysis.outcomes([bar(i, 101) for i in range(0, 20)], 100.0, SIGNAL_TIME, close)
    assert figures["return_pct"]["15m"] is not None
    assert figures["return_pct"]["30m"] is None and figures["return_pct"]["60m"] is None


def test_never_returning_to_start():
    assert analysis.outcomes([bar(1, 105, low=101)], 100.0, SIGNAL_TIME, CLOSE_TIME)["returned_to_start"] is False


async def test_a_pre_mortem_never_sees_later_bars():
    provider = FakeProvider(json.dumps(PRE_REPLY))
    bars = [bar(-1, 100), bar(0, 777.0), bar(1, 888.0)]
    await analysis.run("pre", signal(), bars, CLOSE_TIME, provider)
    sent = json.dumps(provider.calls[0])
    assert "777" not in sent and "888" not in sent


def test_the_pre_mortem_request_has_no_access_to_outcomes():
    assert set(inspect.signature(analysis.pre_request).parameters) == {"signal", "bars"}


async def test_a_pre_mortem_sends_the_same_data_whenever_it_runs():
    early = [bar(-2, 99), bar(-1, 100)]
    late = early + [bar(i, 150) for i in range(0, 300)]
    first, second = FakeProvider(json.dumps(PRE_REPLY)), FakeProvider(json.dumps(PRE_REPLY))
    await analysis.run("pre", signal(), early, CLOSE_TIME, first)
    await analysis.run("pre", signal(), late, CLOSE_TIME, second)
    assert first.calls == second.calls


@pytest.mark.parametrize("kind", ["pre", "post"])
async def test_only_market_data_is_sent(kind):
    reply = PRE_REPLY if kind == "pre" else POST_REPLY
    provider = FakeProvider(json.dumps(reply))
    await analysis.run(kind, signal(), [bar(-1, 100), bar(20, 101)], CLOSE_TIME, provider)
    sent = json.dumps(provider.calls[0]).lower()
    for word in ("account", "position", "balance", "netliquidation", "llm", "notified"):
        assert word not in sent


@pytest.mark.parametrize(
    ("signal_type", "directions"),
    [
        (EMA_CROSS, ["long"]),
        (VWAP_CROSS, ["long"]),
        (VWAP_BAND_ABOVE, ["long"]),
        (VOLUME_SPIKE, ["long", "short"]),
        (VWAP_BAND_BELOW, ["long", "short"]),
    ],
)
def test_direction_by_trigger(signal_type, directions):
    assert analysis.directions_for(signal_type) == directions


async def test_a_post_mortem_gets_computed_figures_and_is_marked_hindsight():
    provider = FakeProvider(json.dumps(POST_REPLY))
    result = await analysis.run("post", signal(VOLUME_SPIKE), [bar(i, 101) for i in range(30)], CLOSE_TIME, provider)
    assert provider.calls[0]["outcome_for_a_long_entry_percent"]["return_pct"]["15m"] == pytest.approx(1)
    assert provider.calls[0]["directions"] == ["long", "short"]
    assert result["verdict"] == "good" and result["hindsight"] is True
    assert result["outcomes"]["return_pct"]["15m"] == pytest.approx(1)
    assert provider.max_tokens == 1500 and provider.schema == analysis.POST_SCHEMA


@pytest.mark.parametrize(
    "reply",
    ["not json", '{"action": "take"}', '{"action": "buy", "confidence": 0.5, "case_for": "a", "risks": "b", "invalidation": "c"}',
     '{"action": "take", "confidence": 2, "case_for": "a", "risks": "b", "invalidation": "c"}',
     '{"action": "take", "confidence": 0.5, "case_for": " ", "risks": "b", "invalidation": "c"}'],
)
async def test_invalid_pre_mortem_replies_are_rejected(reply):
    with pytest.raises(AnalysisError) as err:
        await analysis.run("pre", signal(), [bar(-1, 100)], CLOSE_TIME, FakeProvider(reply))
    assert "invalid reply" in err.value.message


async def test_invalid_verdict_is_rejected():
    with pytest.raises(AnalysisError):
        await analysis.run("post", signal(), [bar(1, 101)], CLOSE_TIME, FakeProvider('{"verdict": "great", "explanation": "x"}'))


async def test_provider_failures_become_readable_errors(monkeypatch):
    with pytest.raises(AnalysisError) as err:
        await analysis.run("pre", signal(), [bar(-1, 100)], CLOSE_TIME, FakeProvider(error=RuntimeError("secret")))
    assert "RuntimeError" in err.value.message and "secret" not in err.value.message
    monkeypatch.setattr(analysis, "TIMEOUT_SECONDS", 0.01)
    with pytest.raises(AnalysisError) as err:
        await analysis.run("pre", signal(), [bar(-1, 100)], CLOSE_TIME, FakeProvider("{}", delay=1.0))
    assert err.value.status == 504


def test_context_bars_are_five_minute_ohlcv():
    bars = [{"time": 300.0 + i * 60, "open": 1 + i, "high": 2 + i, "low": i, "close": 1.5 + i, "volume": 10.0} for i in range(6)]
    rows = analysis.context_bars(bars)
    assert len(rows) == 2
    assert rows[0][1:] == [1, 6, 0, 5.5, 50.0]


def test_post_mortem_timing():
    with pytest.raises(AnalysisError):
        analysis.check_post_mortem_ready(SIGNAL_TIME, CLOSE_TIME, SIGNAL_TIME + timedelta(minutes=14))
    with pytest.raises(AnalysisError):
        analysis.check_post_mortem_ready(CLOSE_TIME - timedelta(minutes=10), CLOSE_TIME, CLOSE_TIME + timedelta(days=1))
    analysis.check_post_mortem_ready(SIGNAL_TIME, CLOSE_TIME, SIGNAL_TIME + timedelta(minutes=15))


# ── Service: storage, errors, and the endpoint ───────────────────────────────


@pytest.fixture
async def world(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    payload = {"category": "technical", "indicators": {"vwap": 99.0}, "bars": [], "llm": {}, "notified": True}
    async with database.AsyncSessionLocal() as session:
        session.add(SignalEvent(id="s1", time=SIGNAL_TIME, signal_type=EMA_CROSS, symbol="SOXL", price=100.0, payload=json.dumps(payload)))
        await session.commit()

    state = SimpleNamespace(provider=FakeProvider(json.dumps(PRE_REPLY)), bars=[bar(-1, 100), bar(30, 101)], connected=True, requests=[])
    monkeypatch.setattr(signal_module, "resolve_provider", lambda app, s: state.provider)
    monkeypatch.setattr(ibkr_service.ibkr, "isConnected", lambda: state.connected)

    async def fake_bars(*args, **kwargs):
        state.requests.append((args, kwargs))
        return state.bars

    monkeypatch.setattr(ibkr_service, "get_historical_bars", fake_bars)
    monkeypatch.setattr(signals_router, "signal_service", SignalService())
    yield state
    await database._engine.dispose()


async def saved(kind):
    page = await signals_router.signal_service.history_page(10)
    return page["signals"][0]["analyses"].get(kind)


async def test_a_result_is_saved_and_shows_in_history(world):
    result = await signals_router.run_analysis("s1", "pre")
    assert result["action"] == "take" and result["provider"] == "fake" and result["model"] == "fake-model"
    stored = await saved("pre")
    assert stored["case_for"] == "Trend" and stored["created_at"].endswith("+00:00")


async def test_a_rerun_replaces_the_result(world):
    await signals_router.run_analysis("s1", "pre")
    world.provider = FakeProvider(json.dumps({**PRE_REPLY, "action": "skip"}))
    await signals_router.run_analysis("s1", "pre")
    assert (await saved("pre"))["action"] == "skip"


async def test_a_failed_rerun_keeps_the_old_result(world):
    await signals_router.run_analysis("s1", "pre")
    world.provider = FakeProvider("not json")
    with pytest.raises(HTTPException) as err:
        await signals_router.run_analysis("s1", "pre")
    assert err.value.status_code == 502
    assert (await saved("pre"))["action"] == "take"


async def test_the_two_kinds_are_saved_separately(world):
    await signals_router.run_analysis("s1", "pre")
    world.provider = FakeProvider(json.dumps(POST_REPLY))
    await signals_router.run_analysis("s1", "post")
    assert (await saved("pre"))["action"] == "take" and (await saved("post"))["verdict"] == "good"


async def test_the_signal_itself_is_left_unchanged(world):
    async with database.AsyncSessionLocal() as session:
        before = (await session.get(SignalEvent, "s1")).payload
    await signals_router.run_analysis("s1", "pre")
    async with database.AsyncSessionLocal() as session:
        assert (await session.get(SignalEvent, "s1")).payload == before


async def test_requests_end_at_the_signals_session(world):
    await signals_router.run_analysis("s1", "pre")
    args, kwargs = world.requests[0]
    assert args[1:3] == ("1 D", "1 min") and kwargs["end"].date() == SIGNAL_TIME.date()


@pytest.mark.parametrize(
    ("change", "status"),
    [
        (lambda w: setattr(w, "provider", None), 400),
        (lambda w: setattr(w, "connected", False), 503),
        (lambda w: setattr(w, "bars", []), 502),
    ],
)
async def test_refused_requests_make_no_provider_call_and_save_nothing(world, change, status):
    provider = world.provider
    change(world)
    with pytest.raises(HTTPException) as err:
        await signals_router.run_analysis("s1", "pre")
    assert err.value.status_code == status
    assert provider.calls == [] and await saved("pre") is None


async def test_unknown_signal_and_kind(world):
    with pytest.raises(HTTPException) as err:
        await signals_router.run_analysis("nope", "pre")
    assert err.value.status_code == 404
    with pytest.raises(HTTPException) as err:
        await signals_router.run_analysis("s1", "other")
    assert err.value.status_code == 422


async def test_a_duplicate_request_is_refused_while_running(world):
    world.provider = FakeProvider(json.dumps(PRE_REPLY), delay=0.05)
    first = asyncio.create_task(signals_router.run_analysis("s1", "pre"))
    await asyncio.sleep(0.01)
    with pytest.raises(HTTPException) as err:
        await signals_router.run_analysis("s1", "pre")
    assert err.value.status_code == 409
    await first


async def test_a_recent_signal_refuses_a_post_mortem(world, monkeypatch):
    class Soon(datetime):
        @classmethod
        def now(cls, tz=None):
            return SIGNAL_TIME + timedelta(minutes=5)

    monkeypatch.setattr(signal_module, "datetime", Soon)
    provider = world.provider
    with pytest.raises(HTTPException) as err:
        await signals_router.run_analysis("s1", "post")
    assert err.value.status_code == 409 and provider.calls == []
