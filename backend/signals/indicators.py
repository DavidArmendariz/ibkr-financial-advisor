import math
from collections import deque
from datetime import datetime
from typing import Callable, Optional

from backend.signals.models import Bar, IndicatorValues


class EMA:
    # Seeded with the first value (pandas ewm(span=period, adjust=False)); reported
    # only once `period` values have been seen.
    def __init__(self, period: int):
        self.period = period
        self.alpha = 2.0 / (period + 1)
        self.value: Optional[float] = None
        self.count = 0

    def update(self, x: float) -> Optional[float]:
        self.value = x if self.value is None else self.alpha * x + (1 - self.alpha) * self.value
        self.count += 1
        return self.value if self.count >= self.period else None


class Bollinger:
    # Population standard deviation over the window, as Bollinger defines it.
    def __init__(self, period: int, k: float):
        self.period = period
        self.k = k
        self.window: deque[float] = deque()
        self.total = 0.0
        self.total_sq = 0.0

    def update(self, x: float) -> Optional[tuple[float, float, float]]:
        self.window.append(x)
        self.total += x
        self.total_sq += x * x
        if len(self.window) > self.period:
            old = self.window.popleft()
            self.total -= old
            self.total_sq -= old * old
        if len(self.window) < self.period:
            return None
        mean = self.total / self.period
        std = math.sqrt(max(self.total_sq / self.period - mean * mean, 0.0))
        return mean, mean + self.k * std, mean - self.k * std


class SessionVWAP:
    # `anchor_for(bar_time)` returns the session start for that bar, or None when
    # the bar falls outside the session (e.g. pre-market when it's excluded).
    def __init__(self, anchor_for: Callable[[datetime], Optional[datetime]]):
        self.anchor_for = anchor_for
        self.anchor: Optional[datetime] = None
        self.pv = 0.0
        self.volume = 0.0

    def update(self, bar: Bar) -> Optional[float]:
        anchor = self.anchor_for(bar.time)
        if anchor is None or bar.time < anchor:
            return None
        if anchor != self.anchor:
            self.anchor, self.pv, self.volume = anchor, 0.0, 0.0
        typical = (bar.high + bar.low + bar.close) / 3
        self.pv += typical * bar.volume
        self.volume += bar.volume
        return self.pv / self.volume if self.volume > 0 else None


class RelativeVolume:
    # Current bar volume against the mean of the previous `period` bars.
    def __init__(self, period: int):
        self.period = period
        self.window: deque[float] = deque(maxlen=period)
        self.total = 0.0

    def update(self, volume: float) -> Optional[float]:
        result = None
        if len(self.window) == self.period and self.total > 0:
            result = volume / (self.total / self.period)
        if len(self.window) == self.period:
            self.total -= self.window[0]
        self.window.append(volume)
        self.total += volume
        return result


class IndicatorSet:
    def __init__(
        self,
        *,
        ema_fast: int,
        ema_slow: int,
        bb_period: int,
        bb_std: float,
        rvol_period: int,
        vwap_anchor_for: Callable[[datetime], Optional[datetime]],
    ):
        self.ema_fast = EMA(ema_fast)
        self.ema_slow = EMA(ema_slow)
        self.bollinger = Bollinger(bb_period, bb_std)
        self.rvol = RelativeVolume(rvol_period)
        self.vwap = SessionVWAP(vwap_anchor_for)

    def update(self, bar: Bar) -> IndicatorValues:
        bands = self.bollinger.update(bar.close)
        return IndicatorValues(
            vwap=self.vwap.update(bar),
            ema_fast=self.ema_fast.update(bar.close),
            ema_slow=self.ema_slow.update(bar.close),
            bb_mid=bands[0] if bands else None,
            bb_upper=bands[1] if bands else None,
            bb_lower=bands[2] if bands else None,
            rvol=self.rvol.update(bar.volume),
        )
