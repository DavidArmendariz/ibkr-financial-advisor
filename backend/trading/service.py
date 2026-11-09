from datetime import datetime, timedelta, timezone

from backend.services import ibkr_service
from backend.trading.broker import Broker
from backend.trading.config import get_trading_settings
from backend.trading.session import TradingSession
from backend.trading.sessions import session_at
from backend.trading.watcher import Watcher

BARS_CACHE = timedelta(seconds=30)

trading_session = TradingSession()
broker = Broker(trading_session)
watcher = Watcher(broker)
_bars: dict[str, tuple[datetime, list[dict]]] = {}


async def chart_bars(symbol: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    cached = _bars.get(symbol)
    if cached and now - cached[0] < BARS_CACHE:
        return cached[1]
    # Two days of 1-minute bars including pre-market and after-hours, on the read-only connection.
    bars = await ibkr_service.get_historical_bars(symbol, "2 D", "1 min", "TRADES", False)
    if bars:
        _bars[symbol] = (now, bars)
    return bars or (cached[1] if cached else [])


async def state() -> dict:
    status = ibkr_service.get_status()
    settings = get_trading_settings()
    accounts = ibkr_service.ibkr.managedAccounts() if status["connected"] else []
    return {
        "connected": status["connected"],
        "mode": status["mode"],
        "account": accounts[0] if len(accounts) == 1 else None,
        "session": session_at(datetime.now(timezone.utc)),
        "trading_session_open": trading_session.connected(),
        "settings": settings.model_dump(),
        "brackets": await broker.brackets(status["mode"]),
    }
