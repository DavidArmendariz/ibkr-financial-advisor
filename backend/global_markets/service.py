import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from backend.global_markets.instruments import ETF, INSTRUMENTS, Instrument
from backend.macro.indicators import change_fields, delay_minutes, is_open, parse_trading_hours
from backend.services import ibkr_service

log = logging.getLogger(__name__)

Hours = list[tuple[datetime, datetime]]

REFRESH_INTERVAL = timedelta(minutes=5)
RESOLVE_INTERVAL = timedelta(days=1)
# Foreign bars can lag, so a market that just closed is read until its last bars are in.
FINAL_DATA_AFTER = timedelta(minutes=30)
BAR_SECONDS = 300
LOOP_SECONDS = 15
REQUEST_TIMEOUT = 20
INFO_CODES = {2100, 2104, 2106, 2107, 2108, 2119, 2158}
ERROR_CODES = {162, 165, 200, 354, 366, 420, 10089, 10090, 10167, 10168, 10197}


@dataclass
class Slot:
    inst: Instrument
    contract: Any = None
    hours: Hours = field(default_factory=list)
    resolved_at: Optional[datetime] = None
    intraday: list[dict] = field(default_factory=list)
    daily: list[dict] = field(default_factory=list)
    tried_at: Optional[datetime] = None
    resolve_tried_at: Optional[datetime] = None
    intraday_at: Optional[datetime] = None
    daily_at: Optional[datetime] = None
    daily_session: Optional[date] = None
    error: Optional[str] = None


def _started(hours: Hours, now: datetime) -> list[tuple[datetime, datetime]]:
    return [h for h in hours if h[0] <= now]


def session_day(hours: Hours, now: datetime) -> Optional[date]:
    started = _started(hours, now)
    return max(started)[0].date() if started else None


def last_close(hours: Hours, now: datetime) -> Optional[datetime]:
    ended = [end for _, end in hours if end <= now]
    return max(ended) if ended else None


def _bar_day(bar: dict) -> date:
    return datetime.fromtimestamp(bar["time"], timezone.utc).date()


def previous_close(daily: list[dict], session: Optional[date]) -> Optional[float]:
    if session is None:
        # liquidHours starts today, so before the open the last session is the newest bar.
        return daily[-2]["close"] if len(daily) >= 2 else None
    earlier = [b for b in daily if _bar_day(b) < session]
    return earlier[-1]["close"] if earlier else None


def last_value(intraday: list[dict], daily: list[dict], market_open: bool) -> Optional[float]:
    # A closed market's daily bar carries the closing auction, which the 5-minute bars miss.
    if market_open and intraday:
        return intraday[-1]["close"]
    if daily:
        return daily[-1]["close"]
    return intraday[-1]["close"] if intraday else None


def latest_session(bars: list[dict], tz: str, regular_end: Optional[time]) -> list[dict]:
    zone = ZoneInfo(tz)
    local = [(b, datetime.fromtimestamp(b["time"], zone)) for b in bars]
    kept = [(b, t) for b, t in local if regular_end is None or t.time() < regular_end]
    if not kept:
        return []
    day = kept[-1][1].date()
    return [b for b, t in kept if t.date() == day]


def _needs_final_data(fetched_at: Optional[datetime], hours: Hours, now: datetime) -> bool:
    closed_at = last_close(hours, now)
    return fetched_at is None or (closed_at is not None and fetched_at < closed_at + FINAL_DATA_AFTER)


def due_intraday(slot: Slot, now: datetime) -> bool:
    if slot.tried_at is not None and now - slot.tried_at < REFRESH_INTERVAL:
        return False
    return is_open(slot.hours, now) or _needs_final_data(slot.intraday_at, slot.hours, now)


def due_daily(slot: Slot, now: datetime) -> bool:
    if slot.tried_at is not None and now - slot.tried_at < REFRESH_INTERVAL:
        return False
    if slot.daily_session != session_day(slot.hours, now) or slot.daily_at is None:
        return True
    return not is_open(slot.hours, now) and _needs_final_data(slot.daily_at, slot.hours, now)


class GlobalMarketsService:
    def __init__(self, instruments: list[Instrument] = INSTRUMENTS) -> None:
        self.slots = [Slot(inst) for inst in instruments]
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        ib = ibkr_service.ibkr
        ib.errorEvent += self._on_error
        ib.disconnectedEvent += self._on_disconnected
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    def state(self) -> dict:
        connected = ibkr_service.get_status()["connected"]
        now = datetime.now(timezone.utc)
        return {"connected": connected, "instruments": [self._card(s, now, connected) for s in self.slots]}

    def _card(self, slot: Slot, now: datetime, connected: bool) -> dict:
        inst = slot.inst
        market_open = is_open(slot.hours, now)
        value = last_value(slot.intraday, slot.daily, market_open)
        prev = previous_close(slot.daily, session_day(slot.hours, now))
        data_time = slot.intraday[-1]["time"] if slot.intraday else None
        return {
            "key": inst.key,
            "label": inst.label,
            "section": inst.section,
            "group": inst.group,
            "currency": inst.currency,
            "unit": "pts" if inst.section == "Indexes" and inst.group != ETF else inst.currency,
            "decimals": inst.decimals,
            "tz": inst.tz,
            "place": inst.place,
            "value": value,
            "previous_close": prev,
            **change_fields(value, prev, "pct"),
            "market_open": market_open,
            "data_time": data_time,
            "delay_minutes": delay_minutes(data_time + BAR_SECONDS, now) if market_open and data_time is not None else None,
            "stale": not connected,
            "error": slot.error,
            "sparkline": [{"time": b["time"], "value": b["close"]} for b in slot.intraday],
        }

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick(datetime.now(timezone.utc))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Global markets loop: %s", type(e).__name__)
            await asyncio.sleep(LOOP_SECONDS)

    async def tick(self, now: datetime) -> None:
        # One at a time, so a refresh isn't a burst of requests on the shared connection.
        for slot in self.slots:
            if not ibkr_service.get_status()["connected"]:
                return
            await self._refresh(slot, now)

    async def _refresh(self, slot: Slot, now: datetime) -> None:
        try:
            if slot.contract is None or slot.resolved_at is None or now - slot.resolved_at >= RESOLVE_INTERVAL:
                if not await self._resolve(slot, now):
                    return
            want_intraday, want_daily = due_intraday(slot, now), due_daily(slot, now)
            if not want_intraday and not want_daily:
                return
            slot.tried_at = now
            if want_intraday:
                # Two days, so before the open the last session is complete.
                bars = latest_session(await self._bars(slot, "2 D", "5 mins"), slot.inst.tz, slot.inst.regular_end)
                if bars:
                    slot.intraday, slot.intraday_at, slot.error = bars, now, None
            if want_daily:
                bars = await self._bars(slot, "10 D", "1 day")
                if bars:
                    # Stored per session, so a new session gets its previous close.
                    slot.daily, slot.daily_at, slot.error = bars, now, None
                    slot.daily_session = session_day(slot.hours, now)
        except asyncio.TimeoutError:
            slot.error = "IBKR didn't answer in time"

    async def _bars(self, slot: Slot, duration: str, size: str) -> list[dict]:
        return await asyncio.wait_for(
            ibkr_service.get_historical_bars(slot.contract, duration, size, "TRADES", True), REQUEST_TIMEOUT
        )

    async def _resolve(self, slot: Slot, now: datetime) -> bool:
        if slot.resolve_tried_at is not None and now - slot.resolve_tried_at < REFRESH_INTERVAL:
            return slot.contract is not None
        slot.resolve_tried_at = now
        contract = slot.inst.make_contract()
        details = await asyncio.wait_for(ibkr_service.ibkr.reqContractDetailsAsync(contract), REQUEST_TIMEOUT)
        if not details:
            slot.error = slot.error or "IBKR has no contract for this"
            return False
        d = details[0]
        slot.contract, slot.resolved_at = d.contract, now
        hours = d.liquidHours or d.tradingHours
        if hours:
            slot.hours = parse_trading_hours(hours, d.timeZoneId)
        return True

    def _on_disconnected(self) -> None:
        for slot in self.slots:
            slot.resolved_at = None
            slot.tried_at = None
            slot.resolve_tried_at = None

    def _on_error(self, req_id: int, code: int, message: str, contract: Any) -> None:
        if code in INFO_CODES or code not in ERROR_CODES:
            return
        con_id = getattr(contract, "conId", None)
        slot = next((s for s in self.slots if s.contract is not None and s.contract.conId == con_id), None)
        if slot is not None:
            slot.error = f"IBKR error {code}: {message.removeprefix('Historical Market Data Service error message:')}"


global_markets_service = GlobalMarketsService()
