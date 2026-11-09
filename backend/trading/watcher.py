import asyncio
import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from sqlmodel import select

from backend import database
from backend.database import TradeBracket, WatchedStop
from backend.services import ibkr_service
from backend.trading.broker import Broker, TradingError
from backend.trading.orders import OVERNIGHT_VENUE
from backend.trading.sessions import OVERNIGHT, session_at

log = logging.getLogger(__name__)

LOOP_SECONDS = 1.0
# Without a fresh quote for this long overnight, the stop counts as not watched.
STALE_QUOTE = timedelta(seconds=30)
RECENT = object()


def valid_quote(bid: Any, ask: Any) -> bool:
    try:
        b, a = float(bid), float(ask)
    except (TypeError, ValueError):
        return False
    return math.isfinite(b) and math.isfinite(a) and 0 < b <= a


def crossed(exit_action: str, level: float, bid: Any, ask: Any) -> bool:
    # On the book, not the last trade: overnight prints are sparse and can be stale.
    if not valid_quote(bid, ask):
        return False
    return float(bid) <= level if exit_action == "SELL" else float(ask) >= level


class Watcher:
    def __init__(self, broker: Broker, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.broker = broker
        self.clock = clock
        self._task: Optional[asyncio.Task] = None
        self._tickers: dict[str, Any] = {}
        self._last_quote: dict[str, datetime] = {}
        self._protected_night: dict[str, str] = {}

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Stop watcher: %s", type(e).__name__)
            await asyncio.sleep(LOOP_SECONDS)

    async def _open_brackets(self) -> list[TradeBracket]:
        async with database.AsyncSessionLocal() as s:
            return list((await s.exec(select(TradeBracket).where(TradeBracket.state == "open"))).all())

    async def _watched(self) -> dict[str, WatchedStop]:
        async with database.AsyncSessionLocal() as s:
            return {w.bracket_id: w for w in (await s.exec(select(WatchedStop).where(WatchedStop.active == True))).all()}  # noqa: E712

    async def tick(self) -> None:
        now = self.clock()
        if session_at(now) != OVERNIGHT:
            self._release()
            return
        brackets = await self._open_brackets()
        if not brackets:
            self._release()
            return
        connected = ibkr_service.get_status()["connected"]
        night = (now - timedelta(hours=12)).date().isoformat()
        if connected:
            for bracket in brackets:
                # A bracket held into the night gets its overnight take profit and watched stop once per night.
                if self._protected_night.get(bracket.id) != night:
                    try:
                        await self.broker.protect_overnight(bracket.id)
                        self._protected_night[bracket.id] = night
                    except TradingError as e:
                        log.warning("Overnight protection for %s: %s", bracket.id, e.message)
        watched = await self._watched()
        for bracket in brackets:
            stop = watched.get(bracket.id)
            if stop is None:
                continue
            quote = await self._quote(bracket.symbol) if connected else None
            if quote is None:
                await self._gap(stop, now, open_gap=True)
                continue
            if quote is RECENT:
                continue
            await self._gap(stop, now, open_gap=False)
            bid, ask = quote
            if crossed(stop.exit_action, stop.level, bid, ask):
                await self.broker.trigger_stop(bracket.id, bid, ask)

    async def _quote(self, symbol: str) -> Any:
        try:
            ib = await self.broker.session.ensure()
        except Exception:
            return None
        ticker = self._tickers.get(symbol)
        if ticker is None:
            contract = await self.broker._contract(ib, symbol, OVERNIGHT_VENUE)
            ib.reqMarketDataType(1)
            ticker = ib.reqMktData(contract, "", False, False)
            self._tickers[symbol] = ticker
        now = self.clock()
        if valid_quote(ticker.bid, ticker.ask):
            self._last_quote[symbol] = now
            return float(ticker.bid), float(ticker.ask)
        last = self._last_quote.get(symbol)
        # A brief gap in the book isn't a gap in watching; a long one is.
        return RECENT if last is not None and now - last <= STALE_QUOTE else None

    async def _gap(self, stop: WatchedStop, now: datetime, open_gap: bool) -> None:
        gaps = json.loads(stop.gaps)
        is_open = bool(gaps) and gaps[-1][1] is None
        if open_gap == is_open:
            return
        if open_gap:
            gaps.append([now.isoformat(), None])
        else:
            gaps[-1][1] = now.isoformat()
        async with database.AsyncSessionLocal() as s:
            row = await s.get(WatchedStop, stop.bracket_id)
            row.gaps = json.dumps(gaps[-20:])
            s.add(row)
            await s.commit()

    def _release(self) -> None:
        ib = self.broker.session.ib
        for ticker in self._tickers.values():
            if ib is not None and ib.isConnected():
                ib.cancelMktData(ticker.contract)
        self._tickers.clear()
        self._last_quote.clear()
