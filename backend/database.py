from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import get_settings


class ChatThread(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    thread_id: str = Field(foreign_key="chatthread.id", index=True)
    role: str = Field(max_length=20)  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SignalEvent(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    time: datetime = Field(index=True)  # bar close
    signal_type: str = Field(max_length=40)
    symbol: str = Field(max_length=20)
    price: float
    payload: str  # JSON: indicators, bars, llm decision, notified


class SignalAnalysis(SQLModel, table=True):
    signal_id: str = Field(primary_key=True)
    kind: str = Field(primary_key=True, max_length=10)  # "pre" | "post"
    created_at: datetime
    provider: str = Field(max_length=40)
    model: str = Field(max_length=120)
    result: str  # JSON


class FundamentalsAnalysis(SQLModel, table=True):
    ticker: str = Field(primary_key=True, max_length=10)
    created_at: datetime
    data_time: datetime  # when the figures it was written from were fetched
    provider: str = Field(max_length=40)
    model: str = Field(max_length=120)
    result: str  # JSON


class TradeBracket(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=40)
    created_at: datetime
    mode: str = Field(index=True, max_length=10)  # "live" | "paper"
    account: str = Field(max_length=20)
    symbol: str = Field(max_length=10)
    direction: str = Field(max_length=5)  # "long" | "short"
    shares: int
    entry: float
    stop: float
    target: float
    session: str = Field(max_length=10)  # session it was placed in
    state: str = Field(index=True, max_length=12)  # working | open | closed | cancelled | rejected
    orders: str = "{}"  # JSON: role -> {order_id, perm_id, status, price, exchange, message}
    warning: Optional[str] = None  # e.g. the position is unprotected
    updated_at: datetime


class WatchedStop(SQLModel, table=True):
    bracket_id: str = Field(primary_key=True, max_length=40)
    level: float
    exit_action: str = Field(max_length=4)  # SELL closes a long, BUY closes a short
    gap_cap_percent: float
    active: bool = True
    triggered_at: Optional[datetime] = None
    exit_order_id: Optional[int] = None
    gaps: str = "[]"  # JSON: [[start, end-or-null], ...] times it wasn't watched overnight


class SignalOutcome(SQLModel, table=True):
    signal_id: str = Field(primary_key=True)
    status: str = Field(max_length=20)  # "measured" | "not_available"
    measured_at: datetime
    move_5m: Optional[float] = None
    move_15m: Optional[float] = None
    move_30m: Optional[float] = None
    max_up: Optional[float] = None
    max_down: Optional[float] = None


class OutcomeBaseline(SQLModel, table=True):
    day: str = Field(primary_key=True, max_length=10)  # YYYY-MM-DD in ET
    # JSON lists by figure: medians can't be combined from daily totals.
    series: str


class TradeFill(SQLModel, table=True):
    exec_id: str = Field(primary_key=True, max_length=60)
    mode: str = Field(index=True, max_length=10)  # "live" | "paper"
    perm_id: int = Field(index=True)
    time: datetime = Field(index=True)  # UTC
    symbol: str = Field(max_length=20)
    asset_class: str = Field(max_length=10)
    currency: str = Field(max_length=10)
    expiry: Optional[str] = Field(default=None, max_length=10)
    strike: Optional[float] = None
    right: Optional[str] = Field(default=None, max_length=4)
    action: str = Field(max_length=4)
    shares: float
    price: float
    venue: str = Field(max_length=20)
    commission: Optional[float] = None
    realized_pnl: Optional[float] = None


class CalendarEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    source: str = Field(index=True, max_length=20)
    name: str = Field(max_length=80)
    category: str = Field(max_length=20)
    importance: str = Field(max_length=10)
    day: str = Field(index=True, max_length=10)  # YYYY-MM-DD in ET
    at: Optional[datetime] = None  # UTC; None when the time isn't known
    timing: Optional[str] = Field(default=None, max_length=20)
    fetched_at: datetime


class CalendarAlert(SQLModel, table=True):
    id: str = Field(primary_key=True)  # event, kind and event time
    sent_at: datetime


class OptionOpenInterest(SQLModel, table=True):
    # IBKR only reports open interest while the market is open; the last value
    # is kept so exposure can still be computed after hours and on weekends.
    con_id: int = Field(primary_key=True)
    open_interest: float
    as_of: datetime


class GammaSnapshot(SQLModel, table=True):
    symbol: str = Field(primary_key=True, max_length=20)
    updated_at: datetime
    payload: str  # JSON: the last computed exposure


_engine = None
AsyncSessionLocal = None


def get_engine():
    global _engine, AsyncSessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
        AsyncSessionLocal = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _engine


async def create_db_and_tables():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
