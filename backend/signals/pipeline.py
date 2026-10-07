from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from backend.signals.config import SignalSettings
from backend.signals.indicators import IndicatorSet
from backend.signals.models import Bar, IndicatorValues
from backend.signals.rules import LONG_ENTRY, cooldown_elapsed, in_blackout, is_long_entry
from backend.signals.sessions import ET, SessionCalendar

SNAPSHOT_BARS = 20


@dataclass
class Candidate:
    signal_type: str
    symbol: str
    time: datetime  # bar close
    price: float
    indicators: IndicatorValues
    bars: list[Bar] = field(default_factory=list)

    def snapshot(self) -> dict:
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "time": self.time.isoformat(),
            "price": self.price,
            "indicators": self.indicators.to_dict(),
            "bars": [b.to_dict() for b in self.bars],
        }


class SignalPipeline:
    def __init__(self, settings: SignalSettings, calendar: Optional[SessionCalendar] = None):
        self.settings = settings
        self.calendar = calendar or SessionCalendar()
        self.indicators = IndicatorSet(
            ema_fast=settings.ema_fast,
            ema_slow=settings.ema_slow,
            bb_period=settings.bb_period,
            bb_std=settings.bb_std,
            rvol_period=settings.rvol_period,
            vwap_anchor_for=lambda t: self.calendar.vwap_anchor(t, settings.include_premarket),
        )
        self.bars: deque[Bar] = deque(maxlen=SNAPSHOT_BARS)
        self.prev: Optional[tuple[Bar, IndicatorValues]] = None
        self.last_fired: dict[str, datetime] = {}
        self.last_values = IndicatorValues()
        self.last_bar: Optional[Bar] = None

    def apply_settings(self, settings: SignalSettings) -> None:
        # Only for settings outside pipeline_key(); indicator changes need a new pipeline.
        self.settings = settings

    def on_bar(self, bar: Bar, emit: bool = True) -> list[Candidate]:
        values = self.indicators.update(bar)
        self.bars.append(bar)
        self.last_bar, self.last_values = bar, values
        prev, self.prev = self.prev, (bar, values)
        if not emit or prev is None or prev[0].time.astimezone(ET).date() != bar.time.astimezone(ET).date():
            return []

        s = self.settings
        close_time = bar.time + timedelta(minutes=s.timeframe_minutes)
        if in_blackout(
            close_time, self.calendar.session_for(bar.time), s.open_blackout_minutes, s.close_blackout_minutes
        ):
            return []

        candidates = []
        if is_long_entry(prev[0].close, prev[1], bar.close, values, s.rvol_threshold) and cooldown_elapsed(
            self.last_fired.get(LONG_ENTRY), close_time, s.cooldown_minutes
        ):
            self.last_fired[LONG_ENTRY] = close_time
            candidates.append(Candidate(LONG_ENTRY, s.symbol, close_time, bar.close, values, list(self.bars)))
        return candidates
