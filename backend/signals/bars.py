from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.signals.models import Bar

REALTIME_BAR_SECONDS = 5


def bucket_start(t: datetime, minutes: int) -> datetime:
    seconds = minutes * 60
    epoch = int(t.timestamp())
    return datetime.fromtimestamp(epoch - epoch % seconds, tz=timezone.utc)


class BarAggregator:
    # Folds 5-second real-time bars into clock-aligned N-minute bars. A bucket is
    # emitted as soon as its last 5-second bar arrives; buckets joined midway
    # (e.g. right after subscribing) are dropped rather than emitted partial.
    def __init__(self, minutes: int):
        self.minutes = minutes
        self._start: Optional[datetime] = None
        self._complete = False
        self._open = self._high = self._low = self._close = 0.0
        self._volume = 0.0
        self._next_expected: Optional[datetime] = None

    def add(self, t: datetime, o: float, h: float, low: float, c: float, v: float) -> Optional[Bar]:
        start = bucket_start(t, self.minutes)
        emitted = None
        if start != self._start:
            emitted = self._flush()
            self._start = start
            self._complete = t == start
            self._open, self._high, self._low, self._close, self._volume = o, h, low, c, v
        else:
            if t != self._next_expected:
                self._complete = False
            self._high = max(self._high, h)
            self._low = min(self._low, low)
            self._close = c
            self._volume += v
        self._next_expected = t + timedelta(seconds=REALTIME_BAR_SECONDS)
        if self._next_expected >= start + timedelta(minutes=self.minutes):
            return self._flush() or emitted
        return emitted

    def _flush(self) -> Optional[Bar]:
        if self._start is None:
            return None
        bar = None
        end = self._start + timedelta(minutes=self.minutes)
        if self._complete and self._next_expected == end:
            bar = Bar(self._start, self._open, self._high, self._low, self._close, self._volume)
        self._start = None
        self._complete = False
        return bar
