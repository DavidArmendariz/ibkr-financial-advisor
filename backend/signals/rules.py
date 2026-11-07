from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.signals.config import SignalSettings
from backend.signals.models import IndicatorValues

VOLUME_SPIKE = "VOLUME_SPIKE"
EMA_CROSS = "EMA_CROSS"
EMA_CROSS_DOWN = "EMA_CROSS_DOWN"
VWAP_CROSS = "VWAP_CROSS"
VWAP_BAND_ABOVE = "VWAP_BAND_ABOVE"
VWAP_BAND_BELOW = "VWAP_BAND_BELOW"
RSI_ABOVE = "RSI_ABOVE"
RSI_BELOW = "RSI_BELOW"

VOLUME = "volume"
TECHNICAL = "technical"


def crosses_above(prev_value: float, prev_level: float, value: float, level: float) -> bool:
    return prev_value <= prev_level and value > level


def crosses_below(prev_value: float, prev_level: float, value: float, level: float) -> bool:
    return prev_value >= prev_level and value < level


def volume_spike(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    return cur.rvol > s.rvol_threshold


def ema_cross(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    if prev is None or prev.ema_fast is None or prev.ema_slow is None:
        return False
    return crosses_above(prev.ema_fast, prev.ema_slow, cur.ema_fast, cur.ema_slow)


def ema_cross_down(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    if prev is None or prev.ema_fast is None or prev.ema_slow is None:
        return False
    return crosses_below(prev.ema_fast, prev.ema_slow, cur.ema_fast, cur.ema_slow)


def vwap_cross(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    if prev is None or prev.vwap is None:
        return False
    return crosses_above(prev_close, prev.vwap, close, cur.vwap)


def _has_band(prev: Optional[IndicatorValues], cur: IndicatorValues) -> bool:
    # A zero spread (first prints of a session) would put the band on VWAP itself.
    return prev is not None and prev.vwap is not None and prev.vwap_std is not None and bool(cur.vwap_std)


def vwap_band_above(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    if not _has_band(prev, cur):
        return False
    n = s.vwap_band_std
    return crosses_above(prev_close, prev.vwap + n * prev.vwap_std, close, cur.vwap + n * cur.vwap_std)


def vwap_band_below(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    if not _has_band(prev, cur):
        return False
    n = s.vwap_band_std
    return prev_close >= prev.vwap - n * prev.vwap_std and close < cur.vwap - n * cur.vwap_std


def rsi_above(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    if prev is None or prev.rsi is None or cur.rsi is None:
        return False
    return crosses_above(prev.rsi, s.rsi_upper, cur.rsi, s.rsi_upper)


def rsi_below(
    prev_close: Optional[float],
    prev: Optional[IndicatorValues],
    close: float,
    cur: IndicatorValues,
    s: SignalSettings,
) -> bool:
    if prev is None or prev.rsi is None or cur.rsi is None:
        return False
    return prev.rsi >= s.rsi_lower and cur.rsi < s.rsi_lower


@dataclass(frozen=True)
class Trigger:
    signal_type: str
    category: str
    setting: str  # the SignalSettings switch
    fires: Callable[..., bool]


TRIGGERS = (
    Trigger(VOLUME_SPIKE, VOLUME, "trigger_volume_enabled", volume_spike),
    Trigger(EMA_CROSS, TECHNICAL, "trigger_ema_enabled", ema_cross),
    Trigger(EMA_CROSS_DOWN, TECHNICAL, "trigger_ema_down_enabled", ema_cross_down),
    Trigger(VWAP_CROSS, TECHNICAL, "trigger_vwap_enabled", vwap_cross),
    Trigger(VWAP_BAND_ABOVE, TECHNICAL, "trigger_vwap_band_enabled", vwap_band_above),
    Trigger(VWAP_BAND_BELOW, TECHNICAL, "trigger_vwap_band_enabled", vwap_band_below),
    Trigger(RSI_ABOVE, TECHNICAL, "trigger_rsi_enabled", rsi_above),
    Trigger(RSI_BELOW, TECHNICAL, "trigger_rsi_enabled", rsi_below),
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
