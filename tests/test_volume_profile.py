from datetime import date, datetime

import pytest

from backend.signals.config import SignalSettings
from backend.signals.models import Bar
from backend.signals.pipeline import SignalPipeline
from backend.signals.sessions import ET, SessionCalendar
from backend.signals.volume_profile import SessionProfile, bucket_size, profile_state

DAY = date(2026, 10, 6)


@pytest.mark.parametrize(("price", "size"), [(4.0, 0.01), (20.0, 0.02), (50.0, 0.05), (80.0, 0.1), (104.0, 0.25), (300.0, 0.5), (600.0, 1.0), (50_000.0, 10.0)])
def test_bucket_follows_price(price, size):
    assert bucket_size(price) == size


def test_volume_spreads_evenly_across_a_bars_range():
    p = SessionProfile(DAY, 80.0)  # $0.10 buckets
    p.add(80.25, 80.05, 300)
    assert p.volumes == {800: 100.0, 801: 100.0, 802: 100.0}


def test_hand_worked_levels():
    p = SessionProfile(DAY, 80.0)
    # Buckets at 80.0: 10, 80.1: 20, 80.2: 40, 80.3: 20, 80.4: 10; total 100.
    for price, volume in ((80.05, 10), (80.15, 20), (80.25, 40), (80.35, 20), (80.45, 10)):
        p.add(price, price, volume)
    levels = p.levels()
    assert levels["poc"] == 80.2
    # 40, then 20 above (ties go up) reaches 60, then 20 below reaches 80 >= 70.
    assert (levels["value_area_low"], levels["value_area_high"]) == (80.1, 80.4)


def test_value_area_takes_the_busier_neighbor():
    p = SessionProfile(DAY, 80.0)
    for price, volume in ((80.05, 5), (80.15, 50), (80.25, 40), (80.35, 5)):
        p.add(price, price, volume)
    assert (p.levels()["poc"], p.levels()["value_area_low"], p.levels()["value_area_high"]) == (80.1, 80.1, 80.3)


def test_one_bucket_session():
    p = SessionProfile(DAY, 80.0)
    p.add(80.01, 80.02, 100)
    assert (p.levels()["poc"], p.levels()["value_area_low"], p.levels()["value_area_high"]) == (80.0, 80.0, 80.1)


def test_gap_between_buckets_is_crossed():
    p = SessionProfile(DAY, 80.0)
    p.add(80.05, 80.05, 50)
    p.add(81.05, 81.05, 50)
    assert p.levels()["value_area_high"] == 81.1


def test_zero_volume_has_no_levels():
    p = SessionProfile(DAY, 80.0)
    p.add(80.0, 80.0, 0)
    assert p.levels() is None and p.to_dict() is None


def settings():
    return SignalSettings.model_construct(ema_fast=3, ema_slow=5, bb_period=5, rvol_period=3, rvol_threshold=1.5, open_blackout_minutes=10, close_blackout_minutes=10, cooldown_minutes=5)


def bar(day, hh, mm, close, volume=1000):
    return Bar(datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET), close, close, close, close, volume)


def noon(day):
    return datetime(day.year, day.month, day.day, 12, tzinfo=ET)


MON, TUE = date(2026, 10, 5), date(2026, 10, 6)


def test_only_regular_hours_count():
    p = SignalPipeline(settings())
    for b in (bar(MON, 9, 29, 80.0), bar(MON, 9, 30, 81.0), bar(MON, 15, 59, 82.0), bar(MON, 16, 0, 90.0)):
        p.on_bar(b)
    prices = {x["price"] for x in p.volume_profile(noon(MON))["bars"]["buckets"]}
    assert prices == {81.0, 82.0}


def test_early_close_follows_the_calendar():
    close = datetime(2026, 11, 27, 13, tzinfo=ET)
    open_ = datetime(2026, 11, 27, 9, 30, tzinfo=ET)
    p = SignalPipeline(settings(), SessionCalendar({date(2026, 11, 27): (open_, close)}))
    p.on_bar(bar(date(2026, 11, 27), 12, 59, 80.0))
    p.on_bar(bar(date(2026, 11, 27), 13, 0, 90.0))
    assert [b["price"] for b in p.volume_profile(noon(date(2026, 11, 27)))["bars"]["buckets"]] == [80.0]


def test_before_the_open_the_bars_are_yesterdays():
    p = SignalPipeline(settings())
    p.on_bar(bar(MON, 10, 0, 80.0))
    state = p.volume_profile(noon(TUE))
    assert state["today"] is None
    assert state["bars"]["session"] == "2026-10-05" and state["yesterday"]["poc"] == 80.0


def test_a_new_session_moves_today_to_yesterday():
    p = SignalPipeline(settings())
    p.on_bar(bar(MON, 10, 0, 80.0))
    p.on_bar(bar(TUE, 10, 0, 90.0))
    state = p.volume_profile(noon(TUE))
    assert state["today"]["poc"] == 90.0 and state["yesterday"]["poc"] == 80.0
    assert state["bars"]["session"] == "2026-10-06"


def test_warmup_bars_count():
    p = SignalPipeline(settings())
    p.on_bar(bar(MON, 10, 0, 80.0), emit=False)
    assert p.volume_profile(noon(MON))["today"]["poc"] == 80.0


def test_yesterdays_levels_outlive_the_chart_history():
    p = SignalPipeline(settings())
    p.on_bar(bar(MON, 9, 30, 80.0, 99_000))
    p.history.clear()
    p.on_bar(bar(TUE, 10, 0, 90.0))
    assert p.volume_profile(noon(TUE))["yesterday"]["poc"] == 80.0


def test_state_is_cached_until_a_bar_or_a_new_day():
    p = SignalPipeline(settings())
    p.on_bar(bar(MON, 10, 0, 80.0))
    first = p.volume_profile(noon(MON))
    assert p.volume_profile(noon(MON)) is first
    p.on_bar(bar(MON, 10, 1, 81.0))
    assert p.volume_profile(noon(MON)) is not first
    second = p.volume_profile(noon(MON))
    assert p.volume_profile(noon(TUE))["today"] is None and second["today"] is not None


def test_no_data_is_empty():
    assert profile_state(None, None, DAY) == {"bars": None, "today": None, "yesterday": None}


def test_profile_raises_no_signals():
    p = SignalPipeline(settings())
    off = dict(trigger_volume_enabled=False, trigger_ema_enabled=False, trigger_rsi_enabled=False, trigger_vwap_band_enabled=False)
    p.apply_settings(SignalSettings.model_construct(**{**settings().__dict__, **off}))
    assert p.on_bar(bar(MON, 10, 0, 80.0)) == []
