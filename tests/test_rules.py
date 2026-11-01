from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.signals import config as signal_config
from backend.signals.config import SignalSettings, save_signal_settings
from backend.signals.models import Bar, IndicatorValues
from backend.signals.pipeline import SignalPipeline
from backend.signals.rules import (
    EMA_CROSS,
    TECHNICAL,
    VOLUME,
    VOLUME_SPIKE,
    RSI_ABOVE,
    RSI_BELOW,
    VWAP_BAND_ABOVE,
    VWAP_BAND_BELOW,
    VWAP_CROSS,
    cooldown_elapsed,
    crosses_above,
    ema_cross,
    in_blackout,
    rsi_above,
    rsi_below,
    volume_spike,
    vwap_band_above,
    vwap_band_below,
    vwap_cross,
)
from backend.signals.sessions import ET, SessionCalendar

PREV = IndicatorValues(vwap=10.0, ema_fast=10.1, ema_slow=10.0, bb_mid=10, bb_upper=11, bb_lower=9, rvol=1.0)
CUR = IndicatorValues(vwap=10.0, ema_fast=10.2, ema_slow=10.0, bb_mid=10, bb_upper=11, bb_lower=9, rvol=2.0)


def test_crosses_above():
    assert crosses_above(9.9, 10.0, 10.1, 10.0)
    assert crosses_above(10.0, 10.0, 10.1, 10.0)
    assert not crosses_above(10.1, 10.0, 10.2, 10.0)  # already above
    assert not crosses_above(9.9, 10.0, 10.0, 10.0)  # touching isn't crossing


def values(**changes):
    return IndicatorValues(**{**CUR.to_dict(), **changes})


def test_volume_fires_above_threshold_on_its_own():
    # No cross of any kind: volume doesn't depend on the technical triggers.
    assert volume_spike(11.0, PREV, 11.0, values(rvol=2.0), settings())
    assert not volume_spike(11.0, PREV, 11.0, values(rvol=1.5), settings())
    assert not volume_spike(11.0, PREV, 11.0, values(rvol=2.0), settings(rvol_threshold=3.0))
    assert volume_spike(None, None, 11.0, values(rvol=2.0), settings())


def test_ema_cross_fires_only_on_the_crossing_bar():
    below = IndicatorValues(vwap=10.0, ema_fast=9.9, ema_slow=10.0, rvol=1.0)
    assert ema_cross(9.0, below, 9.0, values(ema_fast=10.1, rvol=0.1), settings())  # below VWAP, on low volume
    assert not ema_cross(9.0, PREV, 9.0, values(ema_fast=10.2), settings())  # already above
    assert not ema_cross(9.0, below, 9.0, values(ema_fast=9.95), settings())  # still below
    assert not ema_cross(None, None, 9.0, values(ema_fast=10.1), settings())  # no bar this session


def test_vwap_cross_ignores_trend_and_volume():
    assert vwap_cross(9.95, PREV, 10.05, values(ema_fast=9.0, rvol=0.1), settings())
    assert not vwap_cross(10.05, PREV, 10.1, CUR, settings())  # already above
    assert not vwap_cross(9.9, PREV, 9.95, CUR, settings())  # still below
    assert not vwap_cross(None, None, 10.05, CUR, settings())  # no bar this session


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


# ── VWAP band: VWAP 10, spread 1, so N=2 puts the bands at 12 and 8 ─────────


def band(vwap=10.0, std=1.0):
    return values(vwap=vwap, vwap_std=std)


def test_band_above_fires_on_the_cross_only():
    assert vwap_band_above(11.9, band(), 12.1, band(), settings())
    assert not vwap_band_above(12.1, band(), 12.3, band(), settings())  # staying above
    assert not vwap_band_above(11.0, band(), 11.9, band(), settings())  # still inside
    assert vwap_band_above(12.0, band(), 12.1, band(), settings())  # back at the band, crossing again


def test_band_below_fires_on_the_cross_only():
    assert vwap_band_below(8.1, band(), 7.9, band(), settings())
    assert not vwap_band_below(7.9, band(), 7.7, band(), settings())  # staying below
    assert not vwap_band_below(9.0, band(), 8.1, band(), settings())  # still inside


def test_band_follows_the_setting():
    assert not vwap_band_above(11.9, band(), 12.1, band(), settings(vwap_band_std=3.0))
    assert vwap_band_above(12.9, band(), 13.1, band(), settings(vwap_band_std=3.0))
    assert vwap_band_below(7.1, band(), 6.9, band(), settings(vwap_band_std=3.0))


def test_band_needs_a_spread_and_a_bar_this_session():
    for check, close in ((vwap_band_above, 12.1), (vwap_band_below, 7.9)):
        assert not check(10.0, band(), close, band(std=0.0), settings())
        assert not check(None, None, close, band(), settings())


def test_band_ignores_the_other_indicators():
    quiet = band().__class__(**{**band().to_dict(), "ema_fast": 9.0, "rvol": 0.1})
    assert vwap_band_above(11.9, band(), 12.1, quiet, settings())
    assert vwap_band_below(8.1, band(), 7.9, quiet, settings())


def test_band_setting_stays_out_of_the_pipeline_key():
    assert settings(vwap_band_std=1.0).pipeline_key() == settings(vwap_band_std=3.0, trigger_vwap_band_enabled=True).pipeline_key()


def test_band_directions_keep_separate_cooldowns():
    day = date(2026, 10, 6)
    only_band = dict(trigger_volume_enabled=False, trigger_ema_enabled=False, trigger_vwap_band_enabled=True, cooldown_minutes=30)
    p = SignalPipeline(settings(**only_band))
    calm = [bar(day, 10, i, 10.0 + (0.02 if i % 2 else -0.02), 1000) for i in range(20)]
    assert run(p, calm) == []
    assert types(run(p, [bar(day, 10, 20, 12.0, 1000)])) == [VWAP_BAND_ABOVE]
    assert types(run(p, [bar(day, 10, 21, 8.0, 1000)])) == [VWAP_BAND_BELOW]


def test_rsi_above_fires_on_the_cross_only():
    assert rsi_above(None, values(rsi=74.0), 0, values(rsi=76.0), settings())
    assert rsi_above(None, values(rsi=75.0), 0, values(rsi=76.0), settings())  # back at the level, crossing again
    assert not rsi_above(None, values(rsi=76.0), 0, values(rsi=80.0), settings())  # staying above
    assert not rsi_above(None, values(rsi=60.0), 0, values(rsi=74.0), settings())  # still inside


def test_rsi_below_fires_on_the_cross_only():
    assert rsi_below(None, values(rsi=26.0), 0, values(rsi=24.0), settings())
    assert not rsi_below(None, values(rsi=24.0), 0, values(rsi=20.0), settings())  # staying below
    assert not rsi_below(None, values(rsi=40.0), 0, values(rsi=26.0), settings())  # still inside


def test_rsi_follows_the_levels():
    tight = settings(rsi_upper=60.0, rsi_lower=40.0)
    assert rsi_above(None, values(rsi=59.0), 0, values(rsi=61.0), tight)
    assert rsi_below(None, values(rsi=41.0), 0, values(rsi=39.0), tight)
    assert not rsi_above(None, values(rsi=59.0), 0, values(rsi=61.0), settings())


def test_rsi_needs_values_and_a_bar_this_session():
    for check, rsi in ((rsi_above, 80.0), (rsi_below, 20.0)):
        assert not check(None, None, 0, values(rsi=rsi), settings())
        assert not check(None, values(rsi=None), 0, values(rsi=rsi), settings())
        assert not check(None, values(rsi=50.0), 0, values(rsi=None), settings())


def test_rsi_ignores_the_other_indicators():
    quiet = values(rsi=80.0, ema_fast=9.0, rvol=0.1)
    assert rsi_above(None, values(rsi=70.0), 0, quiet, settings())


def test_rsi_levels_apply_live_but_the_period_rebuilds():
    assert settings().pipeline_key() == settings(rsi_upper=60.0, rsi_lower=10.0, trigger_rsi_enabled=True).pipeline_key()
    assert settings().pipeline_key() != settings(rsi_period=7).pipeline_key()


def test_rsi_directions_keep_separate_cooldowns():
    day = date(2026, 10, 6)
    only_rsi = dict(trigger_volume_enabled=False, trigger_ema_enabled=False, trigger_rsi_enabled=True, cooldown_minutes=30, rsi_period=3)
    p = SignalPipeline(settings(**only_rsi))
    calm = [bar(day, 10, i, 10.0 + (0.02 if i % 2 else -0.02), 1000) for i in range(12)]
    assert run(p, calm) == []
    assert types(run(p, [bar(day, 10, 12, 11.0, 1000)])) == [RSI_ABOVE]
    assert types(run(p, [bar(day, 10, 13, 9.0, 1000), bar(day, 10, 14, 8.0, 1000)])) == [RSI_BELOW]


def test_rsi_period_counts_towards_warmup():
    assert SignalSettings.model_construct(ema_fast=3, ema_slow=5, bb_period=5, rvol_period=3, rsi_period=100).warmup_bars() == 301


def test_rsi_levels_must_be_in_order(monkeypatch):
    monkeypatch.setattr(signal_config, "save_env_values", lambda values: None)
    signal_config.get_signal_settings.cache_clear()
    try:
        for bad in ({"rsi_lower": 80.0}, {"rsi_upper": 25.0}, {"rsi_upper": 100.0}):
            with pytest.raises(ValueError):
                save_signal_settings(bad)
    finally:
        signal_config.get_signal_settings.cache_clear()


def test_band_range_is_validated(monkeypatch):
    monkeypatch.setattr(signal_config, "save_env_values", lambda values: None)
    for bad in (0, 5.5):
        with pytest.raises(ValueError):
            save_signal_settings({"vwap_band_std": bad})


# ── Pipeline: rules applied to a bar stream ──────────────────────────────────


def settings(**overrides):
    base = dict(ema_fast=3, ema_slow=5, bb_period=5, rvol_period=3, rvol_threshold=1.5, open_blackout_minutes=10,
                close_blackout_minutes=10, cooldown_minutes=5, trigger_vwap_band_enabled=False,
                trigger_rsi_enabled=False)
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


def types(signals):
    return [s.signal_type for s in signals]


def test_pipeline_emits_trigger_with_snapshot():
    day = date(2026, 10, 6)
    signals = run(SignalPipeline(settings(trigger_ema_enabled=False)), rising_then_cross(day))
    assert types(signals) == [VOLUME_SPIKE]
    snap = signals[0].snapshot()
    assert snap["price"] == 10.2
    assert snap["category"] == VOLUME
    assert set(snap["indicators"]) == {"vwap", "vwap_std", "rsi", "ema_fast", "ema_slow", "bb_mid", "bb_upper", "bb_lower", "rvol"}
    assert 1 <= len(snap["bars"]) <= 20
    assert snap["time"].startswith("2026-10-06T10:14")


def test_defaults_leave_vwap_off():
    fields = SignalSettings.model_fields
    assert fields["trigger_vwap_band_enabled"].default is True
    assert fields["vwap_band_std"].default == 2.0
    assert fields["trigger_rsi_enabled"].default is True
    assert (fields["rsi_period"].default, fields["rsi_upper"].default, fields["rsi_lower"].default) == (14, 75.0, 25.0)
    assert fields["trigger_volume_enabled"].default is True
    assert fields["trigger_ema_enabled"].default is True
    assert fields["trigger_vwap_enabled"].default is False


def test_triggers_on_one_bar_raise_separate_signals():
    day = date(2026, 10, 6)
    signals = run(SignalPipeline(settings(trigger_vwap_enabled=True)), rising_then_cross(day))
    assert types(signals) == [VOLUME_SPIKE, EMA_CROSS, VWAP_CROSS]
    assert [s.category for s in signals] == [VOLUME, TECHNICAL, TECHNICAL]
    assert len({s.time for s in signals}) == 1


def test_all_triggers_off_raises_nothing():
    off = dict(trigger_volume_enabled=False, trigger_ema_enabled=False, trigger_vwap_enabled=False)
    assert run(SignalPipeline(settings(**off)), rising_then_cross(date(2026, 10, 6))) == []


def test_switch_applies_to_the_next_bar():
    bars = rising_then_cross(date(2026, 10, 6))
    s = settings(trigger_volume_enabled=False, trigger_ema_enabled=False)
    p = SignalPipeline(s)
    assert run(p, bars[:-1]) == []
    p.apply_settings(settings(trigger_ema_enabled=False))
    assert types(run(p, bars[-1:])) == [VOLUME_SPIKE]


def test_switches_do_not_rebuild_indicators():
    assert settings().pipeline_key() == settings(trigger_vwap_enabled=True, trigger_ema_enabled=False).pipeline_key()


def test_pipeline_respects_open_blackout():
    day = date(2026, 10, 6)
    bars = [bar(day, 9, 30 + i, 10.0 - i * 0.05, 1000) for i in range(3)] + [bar(day, 9, 33, 10.3, 5000)]
    assert run(SignalPipeline(settings()), bars) == []


def test_cooldown_suppresses_repeat_of_the_same_trigger():
    day = date(2026, 10, 6)
    p = SignalPipeline(settings(cooldown_minutes=30, trigger_ema_enabled=False))
    first = run(p, rising_then_cross(day, 0))
    second = run(p, [bar(day, 10, 14 + i, 9.5, 1000) for i in range(1, 6)] + [bar(day, 10, 20, 10.5, 9000)])
    assert types(first) == [VOLUME_SPIKE] and second == []


def test_cooldowns_do_not_block_other_triggers():
    day = date(2026, 10, 6)
    p = SignalPipeline(settings(cooldown_minutes=30))
    bars = rising_then_cross(day)
    run(p, bars[:-1])
    p.last_fired[VOLUME_SPIKE] = bars[-1].time
    assert types(run(p, bars[-1:])) == [EMA_CROSS]


def test_volume_fires_on_a_session_first_bar_but_crosses_do_not():
    day, next_day = date(2026, 10, 6), date(2026, 10, 7)
    p = SignalPipeline(settings(open_blackout_minutes=0, trigger_vwap_enabled=True))
    run(p, [bar(day, 15, i, 10.0, 1000) for i in range(30)])
    assert types(run(p, [bar(next_day, 9, 30, 12.0, 9000)])) == [VOLUME_SPIKE]


def test_pipeline_warmup_bars_never_emit():
    day = date(2026, 10, 6)
    p = SignalPipeline(settings())
    assert [c for b in rising_then_cross(day) for c in p.on_bar(b, emit=False)] == []


def test_all_triggers_off_can_be_saved(monkeypatch):
    monkeypatch.setattr(signal_config, "save_env_values", lambda values: None)
    signal_config.get_signal_settings.cache_clear()
    try:
        save_signal_settings({"trigger_volume_enabled": False, "trigger_ema_enabled": False, "trigger_vwap_enabled": False})
    finally:
        signal_config.get_signal_settings.cache_clear()


async def test_saved_signal_keeps_its_category(tmp_path, monkeypatch):
    from backend import database
    from backend.signals.pipeline import Candidate
    from backend.signals.service import SignalService

    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    candidate = Candidate(VOLUME_SPIKE, VOLUME, "SOXL", datetime(2026, 10, 6, 10, 14, tzinfo=ET), 10.2, CUR)
    first = SignalService()
    await first._handle_candidate(candidate)
    reloaded = SignalService()
    await reloaded._load_history()
    assert first.history[0]["category"] == VOLUME
    assert (reloaded.history[0]["signal_type"], reloaded.history[0]["category"]) == (VOLUME_SPIKE, VOLUME)
    assert reloaded.history[0]["ema_periods"] == [first.settings.ema_fast, first.settings.ema_slow]
    await database._engine.dispose()


def test_settings_validation(monkeypatch):
    monkeypatch.setattr(signal_config, "save_env_values", lambda values: None)
    with pytest.raises(ValueError):
        save_signal_settings({"ema_fast": 30, "ema_slow": 21})
    with pytest.raises(ValueError):
        save_signal_settings({"timeframe_minutes": 7})
    with pytest.raises(ValueError):
        save_signal_settings({"llm_confidence_threshold": 1.5})


def test_pipeline_keeps_bars_with_their_indicator_values():
    day = date(2026, 10, 6)
    p = SignalPipeline(settings())
    bars = rising_then_cross(day)
    run(p, bars)
    assert [b for b, _ in p.history] == bars
    assert p.history[-1][1] == p.last_values
    assert p.history[0][1].ema_fast is None and p.history[-1][1].ema_fast is not None
