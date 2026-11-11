import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlmodel import delete, select

from backend import database
from backend.calendar_events.config import get_calendar_settings
from backend.database import MoneySupplyMeta, MoneySupplyObservation
from backend.money_supply import calc, sources
from backend.money_supply.sources import SERIES_ID, SourceError
from backend.signals.sessions import ET

log = logging.getLogger(__name__)

REFRESH_INTERVAL = timedelta(hours=6)
RETRY_INTERVAL = timedelta(hours=1)
LOOP_SECONDS = 60
UNITS = "Billions of dollars, seasonally adjusted"


def utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class MoneySupplyService:
    def __init__(self) -> None:
        self.next_refresh: Optional[datetime] = None
        # The key the last refresh used; a different one (added or replaced in
        # Settings) triggers a refresh right away instead of waiting out the interval.
        self.key_used: Optional[str] = None
        self.refreshing = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            try:
                await self.refresh_due(datetime.now(timezone.utc))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Money supply: %s", type(e).__name__)
            await asyncio.sleep(LOOP_SECONDS)

    def due(self, key: str, now: datetime) -> bool:
        if not key:
            return False
        return key != self.key_used or self.next_refresh is None or now >= self.next_refresh

    async def refresh_due(self, now: datetime) -> None:
        key = get_calendar_settings().fred_api_key
        if not self.due(key, now):
            return
        self.key_used = key
        self.refreshing = True
        try:
            async with httpx.AsyncClient(timeout=sources.TIMEOUT) as client:
                fetched = await sources.fetch_m2(client, key, now.astimezone(ET).date())
        except SourceError as e:
            await self._save_error(str(e))
            self.next_refresh = now + RETRY_INTERVAL
            return
        finally:
            self.refreshing = False
        await self._save(fetched, now)
        self.next_refresh = now + REFRESH_INTERVAL

    async def _meta(self, session) -> MoneySupplyMeta:
        return (await session.get(MoneySupplyMeta, SERIES_ID)) or MoneySupplyMeta(series_id=SERIES_ID)

    async def _save(self, fetched: sources.Fetched, now: datetime) -> None:
        async with database.AsyncSessionLocal() as session:
            await session.exec(delete(MoneySupplyObservation).where(MoneySupplyObservation.series_id == SERIES_ID))
            session.add_all(MoneySupplyObservation(series_id=SERIES_ID, month=m, value=v) for m, v in fetched.observations)
            meta = await self._meta(session)
            meta.last_updated = fetched.last_updated.isoformat() if fetched.last_updated else None
            meta.next_release = fetched.next_release.isoformat() if fetched.next_release else None
            meta.fetched_at = now
            meta.error = None
            session.add(meta)
            await session.commit()

    async def _save_error(self, error: str) -> None:
        async with database.AsyncSessionLocal() as session:
            meta = await self._meta(session)
            meta.error = error[:200]
            session.add(meta)
            await session.commit()

    async def state(self, now: Optional[datetime] = None) -> dict:
        now = now or datetime.now(timezone.utc)
        key_set = bool(get_calendar_settings().fred_api_key)
        async with database.AsyncSessionLocal() as session:
            rows = (
                await session.exec(
                    select(MoneySupplyObservation).where(MoneySupplyObservation.series_id == SERIES_ID).order_by(MoneySupplyObservation.month)
                )
            ).all()
            meta = await session.get(MoneySupplyMeta, SERIES_ID)
        observations = [(r.month, r.value) for r in rows]
        error = meta.error if meta else None
        if not key_set:
            status = "no_key"
        elif error and not self.refreshing:
            status = "error"
        elif not observations:
            status = "loading"
        else:
            status = "ok"
        # A release date that has passed is stale until the next refresh replaces it.
        next_release = meta.next_release if meta else None
        if next_release and next_release < now.astimezone(ET).date().isoformat():
            next_release = None
        return {
            "status": status,
            "series": SERIES_ID,
            "units": UNITS,
            "latest": calc.latest_reading(observations),
            "observations": calc.with_growth(observations),
            "last_updated": meta.last_updated if meta else None,
            "next_release": next_release,
            "fetched_at": (utc(meta.fetched_at).isoformat() if meta and meta.fetched_at else None),
            "error": error if key_set else None,
        }


money_supply_service = MoneySupplyService()
