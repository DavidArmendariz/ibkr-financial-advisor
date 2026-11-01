import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Optional

import httpx
from sqlmodel import delete, select

from backend import database
from backend.calendar_events import sources
from backend.calendar_events.config import get_calendar_settings, public_settings
from backend.calendar_events.sources import ET, HIGH, Event, SourceError
from backend.database import CalendarAlert, CalendarEvent

log = logging.getLogger(__name__)

REFRESH_INTERVAL = timedelta(hours=6)
RETRY_INTERVAL = timedelta(hours=1)
VIEW_DAYS = 30
EVENING_TIME = time(18, 0)
SOON_BEFORE = timedelta(minutes=30)
ALERT_GRACE = timedelta(minutes=30)
SOURCE_LABELS = {"fomc": "Federal Reserve", "fred": "FRED", "finnhub": "Finnhub"}


def utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def alert_times(event: CalendarEvent) -> list[tuple[str, datetime]]:
    day = date.fromisoformat(event.day)
    times = []
    if event.importance == HIGH or event.category == "earnings":
        times.append(("evening", datetime.combine(day - timedelta(days=1), EVENING_TIME, ET).astimezone(timezone.utc)))
    at = utc(event.at)
    if event.importance == HIGH and at is not None:
        times.append(("soon", at - SOON_BEFORE))
    return times


def alert_due(when: datetime, event: CalendarEvent, now: datetime) -> bool:
    # Past the grace window it's a stale warning, so it's skipped, not delivered late.
    ends = utc(event.at) or datetime.combine(date.fromisoformat(event.day), time(20, 0), ET).astimezone(timezone.utc)
    return when <= now < when + ALERT_GRACE and now < ends


class CalendarService:
    def __init__(self, broadcast: Optional[Callable[[dict], None]] = None) -> None:
        self.broadcast = broadcast
        self.errors: dict[str, str] = {}
        self.next_refresh: dict[str, datetime] = {}
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    def refresh_now(self) -> None:
        self.next_refresh.clear()

    async def _loop(self) -> None:
        while True:
            try:
                now = datetime.now(timezone.utc)
                await self.refresh_due(now)
                await self.send_alerts(now)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Calendar: %s", type(e).__name__)
            await asyncio.sleep(60)

    async def refresh_due(self, now: datetime) -> None:
        settings = get_calendar_settings()
        today = now.astimezone(ET).date()
        keys = {"fred": settings.fred_api_key, "finnhub": settings.finnhub_api_key}
        due = [s for s in SOURCE_LABELS if now >= self.next_refresh.get(s, now)]
        refused: list[str] = []
        if not due:
            return
        async with httpx.AsyncClient(timeout=sources.TIMEOUT) as client:
            for source in due:
                try:
                    if source == "fomc":
                        events = await sources.fetch_fomc(client, today)
                    elif not keys[source]:
                        self.errors.pop(source, None)
                        self.next_refresh[source] = now + REFRESH_INTERVAL
                        continue
                    elif source == "fred":
                        events = await sources.fetch_fred(client, keys[source], today)
                    else:
                        events, refused = await sources.fetch_earnings(client, keys[source], settings.symbols(), today)
                except SourceError as e:
                    self.errors[source] = str(e)
                    self.next_refresh[source] = now + RETRY_INTERVAL
                    continue
                except (ValueError, KeyError, TypeError):
                    self.errors[source] = f"{SOURCE_LABELS[source]} sent an unexpected reply"
                    self.next_refresh[source] = now + RETRY_INTERVAL
                    continue
                await self._save(source, events, now)
                self.errors.pop(source, None)
                if source == "finnhub" and refused:
                    self.errors[source] = f"Finnhub's plan doesn't cover {', '.join(refused)}"
                self.next_refresh[source] = now + REFRESH_INTERVAL

    async def _save(self, source: str, events: list[Event], now: datetime) -> None:
        async with database.AsyncSessionLocal() as session:
            await session.exec(delete(CalendarEvent).where(CalendarEvent.source == source))
            session.add_all(
                CalendarEvent(
                    id=e.id,
                    source=e.source,
                    name=e.name,
                    category=e.category,
                    importance=e.importance,
                    day=e.day.isoformat(),
                    at=e.at,
                    timing=e.timing,
                    fetched_at=now,
                )
                for e in events
            )
            await session.commit()

    async def _upcoming(self, now: datetime, days: int) -> list[CalendarEvent]:
        today = now.astimezone(ET).date()
        end = today + timedelta(days=days)
        query = select(CalendarEvent).where(CalendarEvent.day >= today.isoformat(), CalendarEvent.day <= end.isoformat())
        async with database.AsyncSessionLocal() as session:
            return list((await session.exec(query)).all())

    async def send_alerts(self, now: datetime) -> None:
        settings = get_calendar_settings()
        enabled = {"evening": settings.alert_evening_enabled, "soon": settings.alert_soon_enabled}
        for event in await self._upcoming(now, 2):
            for kind, when in alert_times(event):
                if not enabled[kind] or not alert_due(when, event, now):
                    continue
                # Keyed with the time, so a rescheduled event can alert at its new time.
                alert_id = f"{event.id}:{kind}:{(utc(event.at) or event.day)}"
                async with database.AsyncSessionLocal() as session:
                    if await session.get(CalendarAlert, alert_id):
                        continue
                    session.add(CalendarAlert(id=alert_id, sent_at=now))
                    await session.commit()
                if self.broadcast:
                    self.broadcast({"type": "calendar", "alert": kind, "event": self._record(event)})

    @staticmethod
    def _record(event: CalendarEvent) -> dict:
        at = utc(event.at)
        return {
            "id": event.id,
            "name": event.name,
            "category": event.category,
            "importance": event.importance,
            "day": event.day,
            "at": at.isoformat() if at else None,
            "timing": event.timing,
            "source": event.source,
        }

    async def state(self, now: Optional[datetime] = None) -> dict:
        now = now or datetime.now(timezone.utc)
        settings = get_calendar_settings()
        events = sorted(await self._upcoming(now, VIEW_DAYS), key=lambda e: (e.day, utc(e.at) or datetime.max.replace(tzinfo=timezone.utc), e.name))
        today = now.astimezone(ET).date().isoformat()
        async with database.AsyncSessionLocal() as session:
            rows = (await session.exec(select(CalendarEvent))).all()
        updated: dict[str, datetime] = {}
        for row in rows:
            fetched = utc(row.fetched_at)
            if row.source not in updated or fetched > updated[row.source]:
                updated[row.source] = fetched
        keys = {"fomc": True, "fred": bool(settings.fred_api_key), "finnhub": bool(settings.finnhub_api_key)}
        return {
            # A release at 08:30 shouldn't linger as "upcoming" after it's out.
            "events": [self._record(e) for e in events if not (e.day == today and e.at and utc(e.at) < now)],
            "sources": [
                {
                    "key": source,
                    "label": label,
                    "configured": keys[source],
                    "updated_at": updated[source].isoformat() if source in updated else None,
                    "error": self.errors.get(source),
                }
                for source, label in SOURCE_LABELS.items()
            ],
            "settings": public_settings(settings),
        }


calendar_service = CalendarService()
