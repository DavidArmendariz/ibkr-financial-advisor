from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)
PREMARKET_OPEN = time(4, 0)


class SessionCalendar:
    # Regular hours default to 09:30-16:00 ET on weekdays; IBKR's liquidHours
    # (from contract details) override that for holidays and early closes.
    def __init__(self, overrides: Optional[dict[date, Optional[tuple[datetime, datetime]]]] = None):
        self.overrides = overrides or {}

    @classmethod
    def from_liquid_hours(cls, liquid_hours: str, tz_id: str = "US/Eastern") -> "SessionCalendar":
        tz = ZoneInfo(tz_id)
        overrides: dict[date, Optional[tuple[datetime, datetime]]] = {}
        for part in filter(None, liquid_hours.split(";")):
            day, _, rest = part.partition(":")
            d = datetime.strptime(day, "%Y%m%d").date()
            if rest == "CLOSED":
                overrides[d] = None
                continue
            start, _, end = part.partition("-")
            open_dt = datetime.strptime(start, "%Y%m%d:%H%M").replace(tzinfo=tz)
            close_dt = datetime.strptime(end, "%Y%m%d:%H%M").replace(tzinfo=tz)
            overrides[d] = (open_dt, close_dt)
        return cls(overrides)

    def session(self, d: date) -> Optional[tuple[datetime, datetime]]:
        if d in self.overrides:
            return self.overrides[d]
        if d.weekday() >= 5:
            return None
        return datetime.combine(d, RTH_OPEN, ET), datetime.combine(d, RTH_CLOSE, ET)

    def session_for(self, t: datetime) -> Optional[tuple[datetime, datetime]]:
        return self.session(t.astimezone(ET).date())

    def vwap_anchor(self, t: datetime, include_premarket: bool) -> Optional[datetime]:
        hours = self.session_for(t)
        if hours is None:
            return None
        open_dt, close_dt = hours
        start = datetime.combine(open_dt.date(), PREMARKET_OPEN, ET) if include_premarket else open_dt
        return start if start <= t < close_dt else None


def minutes(n: int) -> timedelta:
    return timedelta(minutes=n)
