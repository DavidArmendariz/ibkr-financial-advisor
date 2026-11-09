from datetime import datetime, time, timedelta
from typing import Optional

from backend.signals.sessions import ET, SessionCalendar

PRE, REGULAR, AFTER, OVERNIGHT, CLOSED = "pre", "regular", "after", "overnight", "closed"
DAY_SESSIONS = (PRE, REGULAR, AFTER)

EXTENDED_OPEN = time(4, 0)
EXTENDED_CLOSE = time(20, 0)
OVERNIGHT_END = time(3, 50)
# After an early close, extended hours end 4 hours later, not at 20:00.
AFTER_HOURS = timedelta(hours=4)


def _day_bounds(cal: SessionCalendar, day) -> Optional[tuple[datetime, datetime, datetime, datetime]]:
    hours = cal.session(day)
    if hours is None:
        return None
    open_dt, close_dt = hours
    start = datetime.combine(day, EXTENDED_OPEN, ET)
    end = min(datetime.combine(day, EXTENDED_CLOSE, ET), close_dt + AFTER_HOURS)
    return start, open_dt, close_dt, end


def session_at(t: datetime, cal: Optional[SessionCalendar] = None) -> str:
    cal = cal or SessionCalendar()
    local = t.astimezone(ET)
    day = local.date()
    bounds = _day_bounds(cal, day)
    if bounds:
        start, open_dt, close_dt, end = bounds
        if start <= local < open_dt:
            return PRE
        if open_dt <= local < close_dt:
            return REGULAR
        if close_dt <= local < end:
            return AFTER
    # IBKR's overnight session runs from 20:00 to 3:50 into the next trading day,
    # Sunday to Thursday nights.
    if local.time() >= EXTENDED_CLOSE:
        next_day = day + timedelta(days=1)
        if cal.session(next_day) is not None:
            return OVERNIGHT
    if local.time() < OVERNIGHT_END and cal.session(day) is not None:
        return OVERNIGHT
    return CLOSED
