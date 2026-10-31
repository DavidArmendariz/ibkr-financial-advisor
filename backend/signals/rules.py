from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.signals.models import IndicatorValues

VOLUME_SPIKE = "VOLUME_SPIKE"
EMA_CROSS = "EMA_CROSS"
VWAP_CROSS = "VWAP_CROSS"

VOLUME = "volume"
TECHNICAL = "technical"


def crosses_above(prev_value: float, prev_level: float, value: float, level: float) -> bool:
    return prev_value <= prev_level and value > level


def volume_spike(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    rvol_threshold: float,
) -> bool:
    return cur.rvol > rvol_threshold


def ema_cross(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    rvol_threshold: float,
) -> bool:
    if prev is None or prev.ema_fast is None or prev.ema_slow is None:
        return False
    return crosses_above(prev.ema_fast, prev.ema_slow, cur.ema_fast, cur.ema_slow)


def vwap_cross(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    rvol_threshold: float,
) -> bool:
    if prev is None or prev.vwap is None:
        return False
    return crosses_above(prev_close, prev.vwap, close, cur.vwap)


@dataclass(frozen=True)
class Trigger:
    signal_type: str
    category: str
    setting: str  # the SignalSettings switch
    fires: Callable[..., bool]


TRIGGERS = (
    Trigger(VOLUME_SPIKE, VOLUME, "trigger_volume_enabled", volume_spike),
    Trigger(EMA_CROSS, TECHNICAL, "trigger_ema_enabled", ema_cross),
    Trigger(VWAP_CROSS, TECHNICAL, "trigger_vwap_enabled", vwap_cross),
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
