from datetime import date, datetime, timedelta

import pytest

from backend.signals import config as signal_config
from backend.signals.config import SignalSettings, save_signal_settings
from backend.signals.models import Bar, IndicatorValues
from backend.signals.pipeline import SignalPipeline
from backend.signals.rules import LONG_ENTRY, cooldown_elapsed, crosses_above, in_blackout, is_long_entry
from backend.signals.sessions import ET, SessionCalendar

PREV = IndicatorValues(vwap=10.0, ema_fast=10.1, ema_slow=10.0, bb_mid=10, bb_upper=11, bb_lower=9, rvol=1.0)
CUR = IndicatorValues(vwap=10.0, ema_fast=10.2, ema_slow=10.0, bb_mid=10, bb_upper=11, bb_lower=9, rvol=2.0)


def test_crosses_above():
    assert crosses_above(9.9, 10.0, 10.1, 10.0)
    assert crosses_above(10.0, 10.0, 10.1, 10.0)
    assert not crosses_above(10.1, 10.0, 10.2, 10.0)  # already above
    assert not crosses_above(9.9, 10.0, 10.0, 10.0)  # touching isn't crossing


def test_long_entry_when_all_conditions_hold():
    assert is_long_entry(9.95, PREV, 10.05, CUR, rvol_threshold=1.5)


@pytest.mark.parametrize(
    "prev_close, close, cur, why",
    [
        (10.05, 10.10, CUR, "no cross: already above VWAP"),
        (9.95, 9.99, CUR, "no cross: still below VWAP"),
        (9.95, 10.05, IndicatorValues(**{**CUR.to_dict(), "ema_fast": 9.9}), "EMA fast below slow"),
        (9.95, 10.05, IndicatorValues(**{**CUR.to_dict(), "rvol": 1.2}), "relative volume too low"),
        (9.95, 10.05, IndicatorValues(**{**CUR.to_dict(), "rvol": None}), "indicators not ready"),
    ],
)
def test_long_entry_rejected(prev_close, close, cur, why):
    assert not is_long_entry(prev_close, PREV, close, cur, rvol_threshold=1.5), why


def session(day=date(2026, 10, 6)):
    return (datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET), datetime(day.year, day.month, day.day, 16, 0, tzinfo=ET))


@pytest.mark.parametrize(
    "hhmm, blocked",
    [((9, 35), True), ((9, 40), False), ((12, 0), False), ((15, 50), False), ((15, 51), True), ((16, 5), True), ((9, 0), True)],
)
def test_blackout(hhmm, blocked):
    t = datetime(2026, 10, 6, *hhmm, tzinfo=ET)
    assert in_blackout(t, session(), 10, 10) is blocked


def test_blackout_when_market_closed():
    assert in_blackout(datetime(2026, 10, 10, 12, 0, tzinfo=ET), None, 10, 10)


def test_cooldown():
    t0 = datetime(2026, 10, 6, 11, 0, tzinfo=ET)
    assert cooldown_elapsed(None, t0, 5)
    assert not cooldown_elapsed(t0, t0 + timedelta(minutes=4), 5)
    assert cooldown_elapsed(t0, t0 + timedelta(minutes=5), 5)


def test_calendar_from_liquid_hours():
    cal = SessionCalendar.from_liquid_hours(
        "20261126:CLOSED;20261127:0930-20261127:1300;20261130:0930-20261130:1600", "US/Eastern"
    )
    assert cal.session(date(2026, 11, 26)) is None
    assert cal.session(date(2026, 11, 27))[1].hour == 13
    assert cal.session(date(2026, 12, 1))[0].hour == 9  # falls back to regular hours
    assert cal.session(date(2026, 12, 5)) is None  # Saturday


# ── Pipeline: rules applied to a bar stream ──────────────────────────────────


def settings(**overrides):
    base = dict(ema_fast=3, ema_slow=5, bb_period=5, rvol_period=3, rvol_threshold=1.5, open_blackout_minutes=10,
                close_blackout_minutes=10, cooldown_minutes=5)
    return SignalSettings.model_construct(**{**base, **overrides})


def bar(day, hh, mm, close, volume):
    t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET)
    return Bar(t, close, close + 0.02, close - 0.02, close, volume)


def rising_then_cross(day, start_minute=0, hh=10):
    # Steady decline drags price below VWAP, then a high-volume pop crosses back above.
    bars = [bar(day, hh, start_minute + i, 10.0 - i * 0.05, 1000) for i in range(10)]
    bars += [bar(day, hh, start_minute + 10 + i, 9.55 + i * 0.01, 1000) for i in range(3)]
    bars.append(bar(day, hh, start_minute + 13, 10.2, 5000))
    return bars


def run(pipeline, bars):
    out = []
    for b in bars:
        out += pipeline.on_bar(b)
    return out


def test_pipeline_emits_long_entry_with_snapshot():
    day = date(2026, 10, 6)
    signals = run(SignalPipeline(settings()), rising_then_cross(day))
    assert [s.signal_type for s in signals] == [LONG_ENTRY]
    snap = signals[0].snapshot()
    assert snap["price"] == 10.2
    assert set(snap["indicators"]) == {"vwap", "ema_fast", "ema_slow", "bb_mid", "bb_upper", "bb_lower", "rvol"}
    assert 1 <= len(snap["bars"]) <= 20
    assert snap["time"].startswith("2026-10-06T10:14")


def test_pipeline_respects_open_blackout():
    day = date(2026, 10, 6)
    bars = [bar(day, 9, 30 + i, 10.0 - i * 0.05, 1000) for i in range(3)] + [bar(day, 9, 33, 10.3, 5000)]
    assert run(SignalPipeline(settings()), bars) == []


def test_pipeline_cooldown_suppresses_repeat():
    day = date(2026, 10, 6)
    p = SignalPipeline(settings(cooldown_minutes=30))
    first = run(p, rising_then_cross(day, 0))
    second = run(p, [bar(day, 10, 14 + i, 9.5, 1000) for i in range(1, 6)] + [bar(day, 10, 20, 10.5, 9000)])
    assert len(first) == 1 and second == []


def test_pipeline_warmup_bars_never_emit():
    day = date(2026, 10, 6)
    p = SignalPipeline(settings())
    assert [c for b in rising_then_cross(day) for c in p.on_bar(b, emit=False)] == []


def test_settings_validation(monkeypatch):
    monkeypatch.setattr(signal_config, "save_env_values", lambda values: None)
    with pytest.raises(ValueError):
        save_signal_settings({"ema_fast": 30, "ema_slow": 21})
    with pytest.raises(ValueError):
        save_signal_settings({"timeframe_minutes": 7})
    with pytest.raises(ValueError):
        save_signal_settings({"llm_confidence_threshold": 1.5})
