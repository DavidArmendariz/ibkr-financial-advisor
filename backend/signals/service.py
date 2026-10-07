import asyncio
import json
import logging
import math
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ib_async import Stock
from sqlmodel import select

from backend import database
from backend.config import get_settings
from backend.database import SignalEvent
from backend.services import ibkr_service
from backend.signals.bars import BarAggregator
from backend.signals.config import SignalSettings, get_signal_settings
from backend.signals.llm_filter import FilterDecision, filter_snapshot, resolve_provider
from backend.signals.models import Bar
from backend.signals.pipeline import Candidate, SignalPipeline
from backend.signals.sessions import SessionCalendar

log = logging.getLogger(__name__)

HISTORY_SIZE = 50
STREAM_RETRY_SECONDS = 30
PERMISSION_RETRY_SECONDS = 300
SESSION_MINUTES = 390
# Informational TWS codes (market data farm connected, etc.)
INFO_CODES = {2100, 2104, 2106, 2107, 2108, 2119, 2158}
DATA_ERROR_CODES = {162, 200, 354, 366, 420, 10089, 10090, 10167, 10168, 10197}
# Missing market data subscriptions won't fix themselves quickly.
PERMISSION_CODES = {354, 420, 10089, 10090, 10167, 10168}


class SignalService:
    def __init__(self) -> None:
        self.settings: SignalSettings = get_signal_settings()
        self.pipeline: Optional[SignalPipeline] = None
        self.aggregator: Optional[BarAggregator] = None
        self.rt_bars: Any = None
        self.stream = "idle"  # idle | warming_up | streaming | error
        self.error: Optional[str] = None
        self.last_price: Optional[float] = None
        self.last_price_time: Optional[datetime] = None
        self.history: deque[dict] = deque(maxlen=HISTORY_SIZE)
        self.subscribers: set[asyncio.Queue] = set()
        self._restart = False
        self._retry_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self._pending: set[asyncio.Task] = set()
        self._last_status: Optional[dict] = None

    async def start(self) -> None:
        await self._load_history()
        ib = ibkr_service.ibkr
        ib.errorEvent += self._on_error
        ib.disconnectedEvent += self._on_disconnected
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        for task in list(self._pending):
            task.cancel()
        self._teardown()

    # ── State for the UI ────────────────────────────────────────────────────

    def status(self) -> dict:
        s = self.settings
        if ibkr_service.get_status()["connected"]:
            ib_state = "connected"
        elif ibkr_service._target is not None:
            ib_state = "reconnecting"
        else:
            ib_state = "down"
        provider = resolve_provider(get_settings(), s)
        return {
            "ib": ib_state,
            "stream": self.stream,
            "error": self.error,
            "symbol": s.symbol,
            "timeframe_minutes": s.timeframe_minutes,
            "llm": {
                "enabled": s.llm_enabled,
                "configured": provider is not None,
                "provider": provider.name if provider else None,
                "model": provider.model if provider else None,
            },
        }

    def live(self) -> dict:
        p = self.pipeline
        bar = p.last_bar if p else None
        return {
            "last_price": self.last_price,
            "last_price_time": self.last_price_time.isoformat() if self.last_price_time else None,
            "bar_time": bar.time.isoformat() if bar else None,
            "bar_close": bar.close if bar else None,
            "indicators": p.last_values.to_dict() if p else None,
        }

    def snapshot(self) -> dict:
        return {
            "status": self.status(),
            "live": self.live(),
            "history": list(self.history),
            "settings": self.settings.model_dump(),
        }

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.discard(queue)

    def _broadcast(self, event: dict) -> None:
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def _broadcast_status(self, force: bool = False) -> None:
        status = self.status()
        if force or status != self._last_status:
            self._last_status = status
            self._broadcast({"type": "status", "status": status})

    # ── Settings ────────────────────────────────────────────────────────────

    def apply_settings(self, settings: SignalSettings) -> None:
        old, self.settings = self.settings, settings
        if settings.pipeline_key() != old.pipeline_key():
            self._restart = True
            self._retry_at = None
        elif self.pipeline:
            self.pipeline.apply_settings(settings)
        self._broadcast({"type": "settings", "settings": settings.model_dump()})
        self._broadcast_status(force=True)

    # ── Stream lifecycle ────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while True:
            try:
                connected = ibkr_service.get_status()["connected"]
                if not connected:
                    if self.rt_bars is not None or self.stream != "idle":
                        self._teardown()
                        self.stream = "idle"
                elif self._restart or (self.rt_bars is None and self._retry_due()):
                    self._restart = False
                    self._teardown()
                    await self._start_stream()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._teardown()
                self.stream = "error"
                self.error = self.error or f"Stream failed: {e}"
                self._retry_at = datetime.now(timezone.utc) + timedelta(seconds=STREAM_RETRY_SECONDS)
            self._broadcast_status()
            await asyncio.sleep(1)

    def _retry_due(self) -> bool:
        return self._retry_at is None or datetime.now(timezone.utc) >= self._retry_at

    async def _start_stream(self) -> None:
        s = self.settings
        ib = ibkr_service.ibkr
        self.stream, self.error, self._retry_at = "warming_up", None, None
        self._broadcast_status()

        contract = Stock(s.symbol, "SMART", "USD")
        if not await ib.qualifyContractsAsync(contract):
            raise RuntimeError(f"IBKR doesn't recognize {s.symbol}")
        details = await ib.reqContractDetailsAsync(contract)
        calendar = SessionCalendar()
        if details and details[0].liquidHours:
            calendar = SessionCalendar.from_liquid_hours(details[0].liquidHours, details[0].timeZoneId or "US/Eastern")

        pipeline = SignalPipeline(s, calendar)
        sessions = math.ceil(s.warmup_bars() * s.timeframe_minutes / SESSION_MINUTES) + 1
        bar_size = "1 min" if s.timeframe_minutes == 1 else f"{s.timeframe_minutes} mins"
        use_rth = not s.include_premarket
        history = await ib.reqHistoricalDataAsync(
            contract, "", f"{min(sessions + 1, 30)} D", bar_size, "TRADES", use_rth, formatDate=2
        )
        if self.stream == "error":
            raise RuntimeError(self.error or "Historical data request failed")
        now = datetime.now(timezone.utc)
        for b in history:
            start = b.date if isinstance(b.date, datetime) else datetime.combine(b.date, datetime.min.time(), timezone.utc)
            if start + timedelta(minutes=s.timeframe_minutes) > now:
                continue  # still forming
            pipeline.on_bar(Bar(start, b.open, b.high, b.low, b.close, float(b.volume)), emit=False)

        self.pipeline = pipeline
        self.aggregator = BarAggregator(s.timeframe_minutes)
        self.rt_bars = ib.reqRealTimeBars(contract, 5, "TRADES", use_rth)
        self.rt_bars.updateEvent += self._on_realtime_bar
        self.stream = "streaming"
        self._broadcast_status()
        self._broadcast({"type": "live", "live": self.live()})

    def _teardown(self) -> None:
        if self.rt_bars is not None:
            self.rt_bars.updateEvent -= self._on_realtime_bar
            if ibkr_service.ibkr.isConnected():
                try:
                    ibkr_service.ibkr.cancelRealTimeBars(self.rt_bars)
                except Exception:
                    pass
        self.rt_bars = None
        self.aggregator = None

    # ── IBKR callbacks ──────────────────────────────────────────────────────

    def _on_disconnected(self) -> None:
        self.rt_bars = None
        self.aggregator = None
        self.stream = "idle"

    def _on_error(self, req_id: int, code: int, message: str, contract: Any) -> None:
        if code in INFO_CODES:
            return
        if code == 1100:
            self.error = "IBKR lost its connection to IB servers"
        elif code == 1101:
            self.error = None
            self._restart = True  # restored, but subscriptions were lost
        elif code == 1102:
            self.error = None
        elif code in DATA_ERROR_CODES and getattr(contract, "symbol", None) in (None, self.settings.symbol):
            if self.stream in ("warming_up", "streaming"):
                self.error = f"IBKR error {code}: {message}"
                self.stream = "error"
                self._teardown()
                wait = PERMISSION_RETRY_SECONDS if code in PERMISSION_CODES else STREAM_RETRY_SECONDS
                self._retry_at = datetime.now(timezone.utc) + timedelta(seconds=wait)

    def _on_realtime_bar(self, bars: Any, has_new_bar: bool) -> None:
        if not has_new_bar or not bars or self.aggregator is None:
            return
        rb = bars[-1]
        self.last_price, self.last_price_time = rb.close, rb.time
        bar = self.aggregator.add(rb.time, rb.open_, rb.high, rb.low, rb.close, float(rb.volume))
        if bar is not None and self.pipeline is not None:
            for candidate in self.pipeline.on_bar(bar):
                task = asyncio.create_task(self._handle_candidate(candidate))
                self._pending.add(task)
                task.add_done_callback(self._pending.discard)
        self._broadcast({"type": "live", "live": self.live()})

    # ── Signals ─────────────────────────────────────────────────────────────

    async def _handle_candidate(self, candidate: Candidate) -> None:
        s = self.settings
        snapshot = candidate.snapshot()
        if s.llm_enabled:
            decision = await filter_snapshot(snapshot, resolve_provider(get_settings(), s))
        else:
            decision = FilterDecision("unfiltered", reason="LLM filter off")
        notify = decision.action == "unfiltered" or (
            decision.action == "take" and (decision.confidence or 0) >= s.llm_confidence_threshold
        )
        record = {
            "id": str(uuid.uuid4()),
            "time": candidate.time.isoformat(),
            "symbol": candidate.symbol,
            "signal_type": candidate.signal_type,
            "price": candidate.price,
            "indicators": snapshot["indicators"],
            "bars": snapshot["bars"],
            "llm": decision.to_dict(),
            "notified": notify,
        }
        await self._persist(record, candidate.time)
        self.history.appendleft(record)
        self._broadcast({"type": "signal", "signal": record, "notify": notify})

    async def _persist(self, record: dict, time: datetime) -> None:
        try:
            async with database.AsyncSessionLocal() as session:
                payload = {k: record[k] for k in ("indicators", "bars", "llm", "notified")}
                session.add(
                    SignalEvent(
                        id=record["id"],
                        time=time,
                        signal_type=record["signal_type"],
                        symbol=record["symbol"],
                        price=record["price"],
                        payload=json.dumps(payload),
                    )
                )
                await session.commit()
        except Exception as e:
            log.warning("Couldn't save signal: %s", type(e).__name__)

    async def _load_history(self) -> None:
        async with database.AsyncSessionLocal() as session:
            rows = await session.exec(select(SignalEvent).order_by(SignalEvent.time.desc()).limit(HISTORY_SIZE))
            for row in rows.all():
                payload = json.loads(row.payload)
                time = row.time if row.time.tzinfo else row.time.replace(tzinfo=timezone.utc)
                self.history.append(
                    {
                        "id": row.id,
                        "time": time.isoformat(),
                        "symbol": row.symbol,
                        "signal_type": row.signal_type,
                        "price": row.price,
                        **payload,
                    }
                )


signal_service = SignalService()
