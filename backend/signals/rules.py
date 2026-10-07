from datetime import datetime, timedelta
from typing import Optional

from backend.signals.models import IndicatorValues

LONG_ENTRY = "LONG_ENTRY"


def crosses_above(prev_value: float, prev_level: float, value: float, level: float) -> bool:
    return prev_value <= prev_level and value > level


def is_long_entry(
    prev_close: float,
    prev: IndicatorValues,
    close: float,
    cur: IndicatorValues,
    rvol_threshold: float,
) -> bool:
    if not (prev.vwap is not None and cur.ready()):
        return False
    return (
        crosses_above(prev_close, prev.vwap, close, cur.vwap)
        and cur.ema_fast > cur.ema_slow
        and cur.rvol > rvol_threshold
    )


def in_blackout(
    bar_close: datetime,
    session: Optional[tuple[datetime, datetime]],
    open_minutes: int,
    close_minutes: int,
) -> bool:
    # Outside regular hours counts as blackout: signals only fire in the session.
    if session is None:
        return True
    open_dt, close_dt = session
    if not open_dt < bar_close <= close_dt:
        return True
    return bar_close < open_dt + timedelta(minutes=open_minutes) or bar_close > close_dt - timedelta(
        minutes=close_minutes
    )


def cooldown_elapsed(last_fired: Optional[datetime], now: datetime, cooldown_minutes: int) -> bool:
    return last_fired is None or now - last_fired >= timedelta(minutes=cooldown_minutes)
