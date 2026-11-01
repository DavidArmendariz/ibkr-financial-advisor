import math
from datetime import date
from typing import Optional

VALUE_AREA_SHARE = 0.7
BUCKET_SIZES = (0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
BUCKET_PRICE_SHARE = 0.001


def bucket_size(price: float) -> float:
    return next((size for size in BUCKET_SIZES if size >= price * BUCKET_PRICE_SHARE), BUCKET_SIZES[-1])


class SessionProfile:
    def __init__(self, session: date, price: float):
        self.session = session
        # Fixed for the session, so levels don't move as the range grows.
        self.bucket = bucket_size(price)
        self.volumes: dict[int, float] = {}

    def add(self, high: float, low: float, volume: float) -> None:
        # Bars don't say at which price each trade happened, so spread it evenly.
        first, last = math.floor(low / self.bucket), math.floor(high / self.bucket)
        share = volume / (last - first + 1)
        for index in range(first, last + 1):
            self.volumes[index] = self.volumes.get(index, 0.0) + share

    def _price(self, index: int) -> float:
        return round(index * self.bucket, 4)

    def levels(self) -> Optional[dict]:
        total = sum(self.volumes.values())
        if total <= 0:
            return None
        poc = max(sorted(self.volumes), key=lambda i: self.volumes[i])
        first, last = min(self.volumes), max(self.volumes)
        low = high = poc
        covered = self.volumes[poc]
        while covered < total * VALUE_AREA_SHARE and (low > first or high < last):
            above = self.volumes.get(high + 1, 0.0) if high < last else -1.0
            below = self.volumes.get(low - 1, 0.0) if low > first else -1.0
            if above >= below:
                high += 1
                covered += above
            else:
                low -= 1
                covered += below
        return {
            "session": self.session.isoformat(),
            "poc": self._price(poc),
            "value_area_high": self._price(high + 1),
            "value_area_low": self._price(low),
        }

    def to_dict(self) -> Optional[dict]:
        levels = self.levels()
        if levels is None:
            return None
        return {
            **levels,
            "bucket": self.bucket,
            "buckets": [{"price": self._price(i), "volume": self.volumes[i]} for i in sorted(self.volumes)],
        }


def profile_state(current: Optional[SessionProfile], previous: Optional[SessionProfile], today: date) -> dict:
    # Before the open the latest session is yesterday's, so it isn't "today" yet.
    has_today = current is not None and current.session == today
    earlier = previous if has_today else current
    drawn = current if has_today else earlier
    return {
        "bars": drawn.to_dict() if drawn else None,
        "today": current.levels() if has_today else None,
        "yesterday": earlier.levels() if earlier else None,
    }
