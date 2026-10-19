import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ib_async import ContFuture, Contract, Future

from backend.macro.indicators import (
    INDICATORS,
    Indicator,
    change_fields,
    freshness,
    is_open,
    num,
    parse_trading_hours,
)
from backend.macro.trm import TrmFeed
from backend.services import ibkr_service

log = logging.getLogger(__name__)

# Live where the account has a subscription, delayed where it doesn't (free for
# NYMEX, CME and CBOE indexes). It only affects requests made after it is set,
# so Gamma's own reqMarketDataType(2) doesn't change these subscriptions.
DELAYED_FROZEN = 4
RESOLVE_INTERVAL = timedelta(days=1)
BARS_INTERVAL = timedelta(minutes=5)
RETRY_INTERVAL = timedelta(minutes=5)
INFO_CODES = {2100, 2104, 2106, 2107, 2108, 2119, 2158}
# Historical data errors only cost the sparkline; the quote keeps streaming.
HISTORICAL_CODES = {162, 165, 366}
DATA_ERROR_CODES = {200, 354, 420, 10089, 10090, 10168, 10197}
# 162 also covers pacing and empty answers, which pass; a missing subscription doesn't.
NO_PERMISSION = "No market data permissions"


@dataclass
class Slot:
    ind: Indicator
    contract: Optional[Contract] = None
    month: Optional[str] = None
    hours: list[tuple[datetime, datetime]] = field(default_factory=list)
    resolved_at: Optional[datetime] = None
    ticker: Any = None
    error: Optional[str] = None
    # Refused historical data only matters when the card has no other value.
    bars_error: Optional[str] = None
    # Not asked again until the next connection, where permissions can differ.
    bars_denied: bool = False
    retry_at: Optional[datetime] = None
    bars_at: Optional[datetime] = None
    spark: list[dict] = field(default_factory=list)
    daily: list[float] = field(default_factory=list)
    # Last streamed values, kept so the card still shows them after a disconnect.
    last_value: Optional[float] = None
    last_time: Optional[datetime] = None
    last_close: Optional[float] = None


class MacroService:
    def __init__(self, indicators: list[Indicator] = INDICATORS) -> None:
        self.indicators = indicators
        self.slots = [Slot(ind) for ind in indicators if ind.source == "ibkr"]
        self.trm = next((TrmFeed(ind) for ind in indicators if ind.source == "trm"), None)
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        ib = ibkr_service.ibkr
        ib.errorEvent += self._on_error
        ib.disconnectedEvent += self._on_disconnected
        self._task = asyncio.create_task(self._loop())
        if self.trm:
            self.trm.start()

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        if self.trm:
            self.trm.stop()
        for slot in self.slots:
            self._unsubscribe(slot)

    # ── State for the UI ────────────────────────────────────────────────────

    def state(self) -> dict:
        connected = ibkr_service.get_status()["connected"]
        now = datetime.now(timezone.utc)
        slots = {slot.ind.key: slot for slot in self.slots}
        indicators = [
            self.trm.state(now) if ind.source == "trm" else self._indicator_state(slots[ind.key], now, connected)
            for ind in self.indicators
        ]
        return {"connected": connected, "indicators": indicators}

    def _indicator_state(self, slot: Slot, now: datetime, connected: bool) -> dict:
        ind, t = slot.ind, slot.ticker
        market_open = is_open(slot.hours, now)
        stream = num(t.marketPrice()) if t is not None else None
        if stream is not None:
            slot.last_value, slot.last_time = stream, t.time or now
            slot.last_close = num(t.close) or slot.last_close
            slot.error = None

        # Once a market closes, IBKR can roll the stream over to the next session
        # (VIX overnight: last == close, change 0), so closed cards show the last
        # session from the daily bars, which also carry the settlement price.
        use_stream = slot.last_value is not None and (market_open or not slot.daily)
        if use_stream:
            value, updated = slot.last_value, slot.last_time
            prev = slot.last_close or (slot.daily[-2] if len(slot.daily) >= 2 else None)
        else:
            value = slot.daily[-1] if slot.daily else None
            updated = (
                datetime.fromtimestamp(slot.spark[-1]["time"], timezone.utc) + BARS_INTERVAL
                if slot.spark
                else None
            )
            prev = slot.daily[-2] if len(slot.daily) >= 2 else None

        scale = lambda x: x / ind.divisor if x is not None else None
        value, prev = scale(value), scale(prev)
        return {
            "key": ind.key,
            "label": ind.label,
            "unit": ind.unit,
            "change_mode": ind.change_mode,
            "decimals": ind.decimals,
            "contract": slot.contract.localSymbol if slot.contract is not None else None,
            "contract_month": slot.month,
            "value": value,
            "previous_close": prev,
            **change_fields(value, prev, ind.change_mode),
            "market_open": market_open,
            "freshness": freshness(market_open, getattr(t, "marketDataType", None), use_stream and stream is not None),
            "valid_from": None,
            "valid_to": None,
            "updated_at": updated.isoformat() if updated else None,
            "stale": not connected,
            "error": slot.error or (slot.bars_error if value is None else None),
            "sparkline": [{"time": p["time"], "value": p["close"] / ind.divisor} for p in slot.spark],
        }

    # ── Subscriptions ───────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while True:
            try:
                if ibkr_service.get_status()["connected"]:
                    await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Macro loop: %s", type(e).__name__)
            await asyncio.sleep(1)

    async def _tick(self) -> None:
        now = datetime.now(timezone.utc)
        # In parallel, so the last cards don't wait for everyone else's bars after a
        # (re)connect. 2 requests per card stays far below IBKR's 50 open historical requests.
        await asyncio.gather(*(self._tick_slot(slot, now) for slot in self.slots))

    async def _tick_slot(self, slot: Slot, now: datetime) -> None:
        if slot.retry_at is not None and now < slot.retry_at:
            return
        try:
            if slot.resolved_at is None or now - slot.resolved_at >= RESOLVE_INTERVAL:
                await self._resolve(slot, now)
            if slot.ticker is None:
                self._subscribe(slot)
            if not slot.bars_denied and (slot.bars_at is None or now - slot.bars_at >= BARS_INTERVAL):
                slot.bars_at = now
                await self._refresh_bars(slot)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            slot.error = str(e) or type(e).__name__
            slot.retry_at = now + RETRY_INTERVAL

    async def _resolve(self, slot: Slot, now: datetime) -> None:
        ib = ibkr_service.ibkr
        assert slot.ind.make_contract is not None
        wanted = slot.ind.make_contract()
        qualified = [c for c in await ib.qualifyContractsAsync(wanted) if c is not None]
        if not qualified:
            raise RuntimeError(f"IBKR doesn't recognize {wanted.symbol}")
        contract = qualified[0]
        if isinstance(contract, ContFuture):
            # reqMktData doesn't accept CONTFUT; stream the month it points at.
            contract = Future(conId=contract.conId, exchange=contract.exchange)
            await ib.qualifyContractsAsync(contract)
        details = await ib.reqContractDetailsAsync(contract)
        d = details[0] if details else None
        if d is not None and d.tradingHours:
            slot.hours = parse_trading_hours(d.tradingHours, d.timeZoneId)
        if slot.contract is None or slot.contract.conId != contract.conId:
            if slot.contract is not None:
                log.info("Macro %s rolled to %s", slot.ind.key, contract.localSymbol)
            self._unsubscribe(slot)
            slot.contract, slot.bars_at = contract, None
            slot.spark, slot.daily = [], []
            slot.last_value = slot.last_time = slot.last_close = None
        slot.month = d.contractMonth if d is not None and isinstance(contract, Future) else None
        slot.resolved_at = now

    def _subscribe(self, slot: Slot) -> None:
        ib = ibkr_service.ibkr
        ib.reqMarketDataType(DELAYED_FROZEN)
        slot.ticker = ib.reqMktData(slot.contract, "", False, False)
        slot.retry_at = None

    def _unsubscribe(self, slot: Slot) -> None:
        if slot.ticker is not None and ibkr_service.ibkr.isConnected():
            try:
                ibkr_service.ibkr.cancelMktData(slot.ticker.contract)
            except Exception:
                pass
        slot.ticker = None

    async def _refresh_bars(self, slot: Slot) -> None:
        # Futures trade almost around the clock, so the "session" includes the overnight hours.
        spark = await ibkr_service.get_historical_bars(slot.contract, "1 D", "5 mins", "TRADES", use_rth=False)
        if slot.bars_denied:
            return
        daily =await ibkr_service.get_historical_bars(slot.contract, "5 D", "1 day", "TRADES", use_rth=False)
        # Keep the previous bars on an empty answer so a transient error doesn't blank the card.
        if spark:
            slot.spark = spark
        if daily:
            slot.daily = [b["close"] for b in daily]
        if spark or daily:
            slot.bars_error = None

    # ── IBKR callbacks ──────────────────────────────────────────────────────

    def _on_disconnected(self) -> None:
        for slot in self.slots:
            slot.ticker = None
            slot.resolved_at = None
            slot.bars_denied = False

    def _on_error(self, req_id: int, code: int, message: str, contract: Any) -> None:
        if code in INFO_CODES or code == 10167:  # 10167: delayed data instead, shown as such
            return
        if code == 1101:  # restored, but subscriptions were lost
            self._on_disconnected()
            return
        con_id = getattr(contract, "conId", None)
        slot = next((s for s in self.slots if s.contract is not None and s.contract.conId == con_id), None)
        if slot is None:
            return
        if code in HISTORICAL_CODES:
            slot.bars_error = f"IBKR error {code}: {message.removeprefix('Historical Market Data Service error message:')}"
            if code == 162 and NO_PERMISSION in message:
                slot.bars_denied = True
        elif code in DATA_ERROR_CODES:
            slot.error = f"IBKR error {code}: {message}"
            self._unsubscribe(slot)
            slot.retry_at = datetime.now(timezone.utc) + RETRY_INTERVAL


macro_service = MacroService()
