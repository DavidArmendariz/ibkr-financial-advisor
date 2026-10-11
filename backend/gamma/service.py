import asyncio
import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ib_async import Option, Stock
from sqlmodel import select

from backend import database
from backend.database import GammaSnapshot, OptionOpenInterest
from backend.gamma.calc import OptionRow, bs_gamma, summarize, years_to_expiry
from backend.gamma.config import GammaSettings, get_gamma_settings
from backend.services import ibkr_service
from backend.signals.sessions import ET, SessionCalendar

log = logging.getLogger(__name__)

# Stays under IBKR's default of 100 simultaneous market data lines, leaving
# room for the signal stream and the dashboard.
BATCH_SIZE = 80
BATCH_TIMEOUT_OPEN = 10.0
BATCH_TIMEOUT_CLOSED = 4.0  # open interest won't arrive after hours anyway
FROZEN = 2  # IBKR market data type: live while open, last values once closed


def _num(x: Any) -> Optional[float]:
    return x if isinstance(x, (int, float)) and not math.isnan(x) and x >= 0 else None


def _open_interest(ticker: Any) -> Optional[float]:
    # IBKR fills the field matching the contract's right; accept either.
    own, other = (
        (ticker.callOpenInterest, ticker.putOpenInterest)
        if ticker.contract.right == "C"
        else (ticker.putOpenInterest, ticker.callOpenInterest)
    )
    if _num(own) is not None:
        return own
    return other if _num(other) else None


class GammaService:
    def __init__(self) -> None:
        self.result: Optional[dict] = None
        self.refreshing = False
        self.progress: tuple[int, int] = (0, 0)
        self.error: Optional[str] = None
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        self._last_auto: Optional[datetime] = None
        self.calendar = SessionCalendar()

    async def start(self) -> None:
        await self._load_snapshot()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    def state(self) -> dict:
        return {
            "refreshing": self.refreshing,
            "progress": {"done": self.progress[0], "total": self.progress[1]},
            "error": self.error,
            "result": self.result,
            "settings": get_gamma_settings().model_dump(),
            "connected": ibkr_service.get_status()["connected"],
        }

    def trigger(self) -> None:
        if not self.refreshing:
            asyncio.create_task(self.refresh())

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(5)
            try:
                if not ibkr_service.get_status()["connected"] or self.refreshing:
                    continue
                s = get_gamma_settings()
                now = datetime.now(timezone.utc)
                due = self._last_auto is None or now - self._last_auto >= timedelta(minutes=s.refresh_minutes)
                # One refresh after connecting (cached open interest after hours),
                # then on schedule while the market is open.
                if self._last_auto is None or (due and self._market_open(now)):
                    self._last_auto = now
                    await self.refresh()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Gamma refresh loop: %s", type(e).__name__)

    def _market_open(self, now: datetime) -> bool:
        hours = self.calendar.session_for(now)
        return hours is not None and hours[0] <= now < hours[1]

    async def refresh(self) -> None:
        if self._lock.locked():
            return
        async with self._lock:
            self.refreshing, self.error, self.progress = True, None, (0, 0)
            try:
                self.result = await self._compute(get_gamma_settings())
                await self._save_snapshot(self.result)
            except Exception as e:
                self.error = str(e) or type(e).__name__
                log.warning("Gamma refresh failed: %s", self.error)
            finally:
                self.refreshing = False

    async def _compute(self, s: GammaSettings) -> dict:
        ib = ibkr_service.ibkr
        if not ibkr_service.get_status()["connected"]:
            raise RuntimeError("Not connected to IBKR")
        ib.reqMarketDataType(FROZEN)
        now = datetime.now(timezone.utc)
        market_open = self._market_open(now)

        stock = Stock(s.symbol, "SMART", "USD")
        if not await ib.qualifyContractsAsync(stock):
            raise RuntimeError(f"IBKR doesn't recognize {s.symbol}")
        spot = await self._spot(stock)
        if spot is None:
            raise RuntimeError(f"No {s.symbol} price available")

        chains = await ib.reqSecDefOptParamsAsync(s.symbol, "", "STK", stock.conId)
        chain = next((c for c in chains if c.exchange == "SMART" and c.tradingClass == s.symbol), None) or next(
            (c for c in chains if c.exchange == "SMART"), None
        )
        if chain is None:
            raise RuntimeError(f"No option chain for {s.symbol}")
        today = now.astimezone(ET).date()
        last_day = today + timedelta(days=s.max_days)
        expirations = sorted(
            e for e in chain.expirations if today <= datetime.strptime(e, "%Y%m%d").date() <= last_day
        )
        lo, hi = spot * (1 - s.strike_range_pct / 100), spot * (1 + s.strike_range_pct / 100)

        contracts = []
        for exp in expirations:
            details = await ib.reqContractDetailsAsync(
                Option(s.symbol, exp, exchange="SMART", currency="USD", tradingClass=chain.tradingClass)
            )
            contracts += [d.contract for d in details if lo <= d.contract.strike <= hi]
        if not contracts:
            raise RuntimeError("No option contracts in range")

        cached = await self._cached_oi([c.conId for c in contracts])
        rows, fresh_oi = [], {}
        oi_live = oi_cached = oi_missing = 0
        self.progress = (0, len(contracts))
        for start in range(0, len(contracts), BATCH_SIZE):
            batch = contracts[start : start + BATCH_SIZE]
            tickers = [ib.reqMktData(c, "101", False, False) for c in batch]
            await self._wait_for(tickers, BATCH_TIMEOUT_OPEN if market_open else BATCH_TIMEOUT_CLOSED)
            for c in batch:
                ib.cancelMktData(c)
            for c, t in zip(batch, tickers):
                oi = _open_interest(t)
                if oi is not None:
                    fresh_oi[c.conId] = oi
                    oi_live += 1
                elif c.conId in cached:
                    oi, oi_cached = cached[c.conId][0], oi_cached + 1
                else:
                    oi_missing += 1
                    continue
                g = t.modelGreeks
                iv = _num(g.impliedVol) if g else None
                gamma = _num(g.gamma) if g else None
                expiry = datetime.strptime(c.lastTradeDateOrContractMonth, "%Y%m%d").date()
                if gamma is None and iv:
                    gamma = bs_gamma(spot, c.strike, years_to_expiry(expiry, now), iv, s.risk_free_rate)
                rows.append(
                    OptionRow(expiry, c.strike, c.right, oi, gamma, iv, float(c.multiplier or 100))
                )
            self.progress = (min(start + BATCH_SIZE, len(contracts)), len(contracts))

        if fresh_oi:
            await self._store_oi(fresh_oi, now)
        if not rows:
            raise RuntimeError(
                "No open interest yet: IBKR only reports it while the market is open. "
                "It will be saved on the first refresh during market hours."
            )
        result = summarize(rows, spot, now, s.risk_free_rate)
        cached_dates = [cached[c][1] for c in cached if c not in fresh_oi]
        result.update(
            symbol=s.symbol,
            updated_at=now.isoformat(),
            market_open=market_open,
            expirations=[datetime.strptime(e, "%Y%m%d").date().isoformat() for e in expirations],
            strike_range=[lo, hi],
            open_interest={
                "live": oi_live,
                "cached": oi_cached,
                "missing": oi_missing,
                "cached_as_of": min(cached_dates).isoformat() if oi_cached and cached_dates else None,
            },
        )
        return result

    async def _spot(self, stock: Stock) -> Optional[float]:
        ib = ibkr_service.ibkr
        ticker = ib.reqMktData(stock, "", False, False)
        for _ in range(20):
            await asyncio.sleep(0.25)
            price = ticker.marketPrice()
            if _num(price):
                break
        ib.cancelMktData(stock)
        price = ticker.marketPrice()
        return price if _num(price) else _num(ticker.close)

    @staticmethod
    async def _wait_for(tickers: list, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.5)
            if all(t.modelGreeks is not None and _open_interest(t) is not None for t in tickers):
                return

    # ── Persistence ────────────────────────────────────────────────────────

    async def _cached_oi(self, con_ids: list[int]) -> dict[int, tuple[float, datetime]]:
        async with database.AsyncSessionLocal() as session:
            rows = await session.exec(select(OptionOpenInterest).where(OptionOpenInterest.con_id.in_(con_ids)))
            return {
                r.con_id: (r.open_interest, r.as_of if r.as_of.tzinfo else r.as_of.replace(tzinfo=timezone.utc))
                for r in rows.all()
            }

    async def _store_oi(self, values: dict[int, float], as_of: datetime) -> None:
        async with database.AsyncSessionLocal() as session:
            for con_id, oi in values.items():
                await session.merge(OptionOpenInterest(con_id=con_id, open_interest=oi, as_of=as_of))
            await session.commit()

    async def _save_snapshot(self, result: dict) -> None:
        async with database.AsyncSessionLocal() as session:
            await session.merge(
                GammaSnapshot(
                    symbol=result["symbol"],
                    updated_at=datetime.fromisoformat(result["updated_at"]),
                    payload=json.dumps(result),
                )
            )
            await session.commit()

    async def _load_snapshot(self) -> None:
        async with database.AsyncSessionLocal() as session:
            row = await session.get(GammaSnapshot, get_gamma_settings().symbol)
            if row:
                self.result = json.loads(row.payload)


gamma_service = GammaService()
