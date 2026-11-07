import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from ib_async import Stock

from backend.planner.calc import completed_days
from backend.rotation import calc
from backend.rotation.config import get_rotation_settings
from backend.services import ibkr_service
from backend.signals.sessions import ET

log = logging.getLogger(__name__)

BENCHMARK = "SPY"
SECTORS = [
    ("XLK", "Technology"),
    ("SMH", "Semiconductors"),
    ("XLC", "Communication Services"),
    ("XLY", "Consumer Discretionary"),
    ("XLF", "Financials"),
    ("XLI", "Industrials"),
    ("XLB", "Materials"),
    ("XLE", "Energy"),
    ("XLV", "Health Care"),
    ("XLP", "Consumer Staples"),
    ("XLU", "Utilities"),
    ("XLRE", "Real Estate"),
]
DURATION = "2 Y"
# Readings sent per timeframe: enough for the longest tail.
POINTS_SENT = 20
# The daily bar settles a little after the 16:00 close.
FINAL_AFTER = time(16, 20)
RETRY_AFTER = timedelta(minutes=5)
LOOP_SECONDS = 60
REQUEST_TIMEOUT = 30
INFO_CODES = {2100, 2104, 2106, 2107, 2108, 2119, 2158}
ERROR_CODES = {162, 165, 200, 354, 366, 420, 10089, 10090, 10167, 10168, 10197}


@dataclass
class Series:
    symbol: str
    name: str = ""
    contract: Any = None
    bars: list[dict] = field(default_factory=list)
    session: Optional[date] = None
    error: Optional[str] = None


def latest_session(now: datetime) -> date:
    # The newest session whose daily bar is final; weekends roll back to Friday.
    local = now.astimezone(ET)
    day = local.date() if local.time() >= FINAL_AFTER else local.date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


class RotationService:
    def __init__(self) -> None:
        self.spy = Series(BENCHMARK, "S&P 500")
        self.etfs = [Series(symbol, name) for symbol, name in SECTORS]
        self.fetched_at: Optional[datetime] = None
        self.tried_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        ibkr_service.ibkr.errorEvent += self._on_error
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    def due(self, now: datetime) -> bool:
        if self.tried_at is not None and now - self.tried_at < RETRY_AFTER:
            return False
        session = latest_session(now)
        return any(series.session != session for series in [self.spy, *self.etfs])

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick(datetime.now(timezone.utc))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Rotation loop: %s", type(e).__name__)
            await asyncio.sleep(LOOP_SECONDS)

    async def tick(self, now: datetime) -> None:
        if not ibkr_service.get_status()["connected"] or not self.due(now):
            return
        self.tried_at, session = now, latest_session(now)
        # One at a time, so a refresh isn't a burst of requests on the shared connection.
        # Only the series still missing this session are asked again.
        for series in [self.spy, *self.etfs]:
            if series.session == session:
                continue
            if not ibkr_service.get_status()["connected"]:
                return
            if await self._fetch(series, now):
                series.session, self.fetched_at = session, now

    async def _fetch(self, series: Series, now: datetime) -> bool:
        try:
            if series.contract is None:
                contract = Stock(series.symbol, "SMART", "USD")
                qualified = await asyncio.wait_for(ibkr_service.ibkr.qualifyContractsAsync(contract), REQUEST_TIMEOUT)
                if not qualified or not getattr(qualified[0], "conId", 0):
                    series.error = "IBKR has no contract for this"
                    return False
                series.contract = qualified[0]
            series.error = None
            bars = await asyncio.wait_for(
                ibkr_service.get_historical_bars(series.contract, DURATION, "1 day", "TRADES", True), REQUEST_TIMEOUT
            )
        except asyncio.TimeoutError:
            series.error = "IBKR didn't answer in time"
            return False
        if not bars:
            # Keep the last bars; an error event may already have said why.
            series.error = series.error or "IBKR returned no bars"
            return False
        series.bars = completed_days(bars, now)
        return True

    def _on_error(self, req_id: int, code: int, message: str, contract: Any) -> None:
        if code in INFO_CODES or code not in ERROR_CODES:
            return
        con_id = getattr(contract, "conId", None)
        if not con_id:
            return
        for series in [self.spy, *self.etfs]:
            if series.contract is not None and series.contract.conId == con_id:
                series.error = f"IBKR error {code}: {message.removeprefix('Historical Market Data Service error message:')}"

    def _readings(self, series: Series, timeframe: str) -> list[dict]:
        if not series.bars or not self.spy.bars:
            return []
        etf, spy = series.bars, self.spy.bars
        if timeframe == "weekly":
            etf, spy = calc.weekly(etf), calc.weekly(spy)
        return calc.readings(calc.relative_strength(etf, spy))

    def state(self) -> dict:
        connected = ibkr_service.get_status()["connected"]
        rows = []
        for series in self.etfs:
            row = {"symbol": series.symbol, "name": series.name, "error": series.error}
            for timeframe in ("weekly", "daily"):
                points = self._readings(series, timeframe)
                row[timeframe] = {"points": points[-POINTS_SENT:], "periods": calc.periods_in_quadrant(points)}
            rows.append(row)
        last = self.spy.bars[-1]["time"] if self.spy.bars else None
        return {
            "connected": connected,
            "stale": not connected and self.fetched_at is not None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "last_session": last,
            "benchmark": {"symbol": BENCHMARK, "error": self.spy.error},
            "lookback": calc.LOOKBACK,
            "settings": get_rotation_settings().model_dump(),
            "etfs": rows,
        }


rotation_service = RotationService()
