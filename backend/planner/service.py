import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ib_async import Stock

from backend.macro.indicators import num
from backend.planner.calc import aggregate, atr_from_bars, completed_days
from backend.services import ibkr_service
from backend.signals.config import get_signal_settings
from backend.signals.service import signal_service

log = logging.getLogger(__name__)

SYMBOLS = ("SOXL", "SOXS")
INTRADAY_REFRESH = timedelta(seconds=60)
DAILY_REFRESH = timedelta(hours=1)
DAILY_ATR_PERIOD = 14
REQUEST_TIMEOUT = 20
ERROR_CODES = {162, 200, 354, 366, 420, 10089, 10090, 10167, 10168, 10197}
# Quotes stream only while someone is looking: two market data lines, dropped when idle.
QUOTE_IDLE = timedelta(minutes=2)
IDLE_CHECK_SECONDS = 30
REAL_TIME = 1


@dataclass
class Quote:
    price: Optional[float] = None
    price_time: Optional[datetime] = None
    intraday_atr: Optional[float] = None
    intraday_time: Optional[datetime] = None
    intraday_at: Optional[datetime] = None
    daily_atr: Optional[float] = None
    daily_time: Optional[datetime] = None
    daily_at: Optional[datetime] = None
    error: Optional[str] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    quote_time: Optional[datetime] = None
    quote_delayed: bool = False


class PlannerService:
    def __init__(self) -> None:
        self.quotes = {symbol: Quote() for symbol in SYMBOLS}
        self._lock = asyncio.Lock()
        self.tickers: dict[str, Any] = {}
        self._wanted_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        ibkr_service.ibkr.errorEvent += self._on_error
        ibkr_service.ibkr.disconnectedEvent += self._on_disconnected
        self._task = asyncio.create_task(self._idle_loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
        self.unsubscribe()

    async def subscribe(self, now: datetime) -> None:
        self._wanted_at = now
        if self.tickers or not ibkr_service.ibkr.isConnected():
            return
        ib = ibkr_service.ibkr
        # reqMktData needs qualified contracts: ib_async keys tickers by conId.
        contracts = [Stock(symbol, "SMART", "USD") for symbol in SYMBOLS]
        await asyncio.wait_for(ib.qualifyContractsAsync(*contracts), REQUEST_TIMEOUT)
        # The market data type applies to requests made after it, and Gamma and
        # Macro set their own, so ask for real time right before subscribing.
        ib.reqMarketDataType(REAL_TIME)
        for contract in contracts:
            if contract.conId:
                self.tickers[contract.symbol] = ib.reqMktData(contract, "", False, False)

    def unsubscribe(self) -> None:
        for ticker in self.tickers.values():
            try:
                if ibkr_service.ibkr.isConnected():
                    ibkr_service.ibkr.cancelMktData(ticker.contract)
            except Exception:
                pass
        self.tickers = {}

    def drop_if_idle(self, now: datetime) -> None:
        if self.tickers and (self._wanted_at is None or now - self._wanted_at >= QUOTE_IDLE):
            self.unsubscribe()

    async def _idle_loop(self) -> None:
        while True:
            await asyncio.sleep(IDLE_CHECK_SECONDS)
            self.drop_if_idle(datetime.now(timezone.utc))

    def _on_disconnected(self) -> None:
        self.tickers = {}

    def _live_soxl(self) -> Optional[Quote]:
        # SOXL already streams for Signals, so its ATR and price come from there.
        p = signal_service.pipeline
        if p is None or p.last_bar is None or p.last_values.atr is None:
            return None
        bar_end = p.last_bar.time + timedelta(minutes=signal_service.settings.timeframe_minutes)
        price_time = signal_service.last_price_time or bar_end
        return Quote(
            price=signal_service.last_price or p.last_bar.close,
            price_time=price_time,
            intraday_atr=p.last_values.atr,
            intraday_time=bar_end,
        )

    async def refresh(self, now: datetime) -> None:
        if not ibkr_service.ibkr.isConnected():
            return
        try:
            await self.subscribe(now)
        except Exception as e:
            # Quotes are a bonus on top of bars, so the rest of the planner still loads.
            log.warning("Planner quotes failed: %s", type(e).__name__)
        async with self._lock:
            for symbol, quote in self.quotes.items():
                try:
                    if (symbol != "SOXL" or self._live_soxl() is None) and (
                        quote.intraday_at is None or now - quote.intraday_at >= INTRADAY_REFRESH
                    ):
                        await self._refresh_intraday(symbol, quote, now)
                    if quote.daily_at is None or now - quote.daily_at >= DAILY_REFRESH:
                        await self._refresh_daily(symbol, quote, now)
                except asyncio.TimeoutError:
                    quote.error = "IBKR didn't answer in time"

    async def _bars(self, symbol: str, duration: str, size: str, rth: bool) -> list[dict]:
        contract = Stock(symbol, "SMART", "USD")
        return await asyncio.wait_for(
            ibkr_service.get_historical_bars(contract, duration, size, "TRADES", rth), REQUEST_TIMEOUT
        )

    async def _refresh_intraday(self, symbol: str, quote: Quote, now: datetime) -> None:
        s = get_signal_settings()
        quote.intraday_at = now
        bars = await self._bars(symbol, "2 D", "1 min", not s.include_premarket)
        if not bars:
            quote.error = quote.error or f"IBKR returned no {symbol} bars"
            return
        last_end = datetime.fromtimestamp(bars[-1]["time"] + 60, timezone.utc)
        quote.price, quote.price_time = bars[-1]["close"], last_end
        quote.intraday_atr = atr_from_bars(aggregate([dict(b) for b in bars], s.timeframe_minutes), s.atr_period)
        quote.intraday_time, quote.error = last_end, None

    async def _refresh_daily(self, symbol: str, quote: Quote, now: datetime) -> None:
        quote.daily_at = now
        bars = completed_days(await self._bars(symbol, "40 D", "1 day", True), now)
        if not bars:
            quote.error = quote.error or f"IBKR returned no {symbol} daily bars"
            return
        quote.daily_atr = atr_from_bars(bars, DAILY_ATR_PERIOD)
        quote.daily_time = datetime.fromtimestamp(bars[-1]["time"], timezone.utc)
        quote.error = None

    def quote(self, symbol: str) -> Quote:
        stored = self.quotes[symbol]
        live = self._live_soxl() if symbol == "SOXL" else None
        q = stored if live is None else Quote(
            price=live.price,
            price_time=live.price_time,
            intraday_atr=live.intraday_atr,
            intraday_time=live.intraday_time,
            daily_atr=stored.daily_atr,
            daily_time=stored.daily_time,
            error=stored.error,
        )
        ticker = self.tickers.get(symbol)
        if ticker is None:
            return q
        bid, ask = num(ticker.bid), num(ticker.ask)
        # A crossed book is a stale quote, not a price anyone can trade at.
        if bid is not None and ask is not None and bid > ask:
            bid = ask = None
        return Quote(
            **{**q.__dict__, "bid": bid, "ask": ask, "quote_time": ticker.time, "quote_delayed": ticker.marketDataType in (3, 4)}
        )

    def quote_state(self, symbol: str) -> dict:
        q = self.quote(symbol)
        iso = lambda t: t.isoformat() if t else None  # noqa: E731
        pct = lambda atr: atr / q.price * 100 if atr is not None and q.price else None  # noqa: E731
        return {
            "symbol": symbol,
            "price": q.price,
            "price_time": iso(q.price_time),
            "intraday_atr": q.intraday_atr,
            "intraday_pct": pct(q.intraday_atr),
            "intraday_time": iso(q.intraday_time),
            "daily_atr": q.daily_atr,
            "daily_pct": pct(q.daily_atr),
            "daily_time": iso(q.daily_time),
            "bid": q.bid,
            "ask": q.ask,
            "quote_time": iso(q.quote_time),
            "quote_delayed": q.quote_delayed,
            "error": q.error,
        }

    def _on_error(self, req_id: int, code: int, message: str, contract: Any) -> None:
        symbol = getattr(contract, "symbol", None)
        if symbol in self.quotes and code in ERROR_CODES:
            self.quotes[symbol].error = f"IBKR error {code}: {message.removeprefix('Historical Market Data Service error message:')}"


planner_service = PlannerService()
