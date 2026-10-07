import asyncio
import calendar
from datetime import datetime
from typing import Optional
from ib_async import IB, Stock, Forex

from backend.config import get_settings

# Only ib_async's *Async APIs are used, awaited on FastAPI's own event loop,
# so no nest_asyncio patching is needed (and it can't patch uvloop anyway).

ibkr = IB()

_connected_port: Optional[int] = None
# Set by a successful connect and cleared by an explicit disconnect; while set,
# supervise() reconnects after drops (IB Gateway's nightly restart, network blips).
_target: Optional[tuple[str, int, int]] = None
reconnecting = False

RECONNECT_MAX_DELAY = 60.0


# Serializes connection attempts: the UI's launch-time auto-connect and a
# button click (or React's dev double-mount) can otherwise race on the socket.
_connect_lock = asyncio.Lock()


async def connect(host: str, port: int, client_id: int) -> bool:
    async with _connect_lock:
        return await _connect(host, port, client_id)


async def _connect(host: str, port: int, client_id: int) -> bool:
    global _connected_port, _target
    if ibkr.isConnected():
        if _connected_port == port:
            return True
        ibkr.disconnect()

    try:
        # readonly: the app only reads data. Without it ib_async requests open and
        # completed orders on connect, which TWS rejects (with a pop-up) when
        # "Read-Only API" is enabled.
        await ibkr.connectAsync(host, port, clientId=client_id, timeout=5, readonly=True)
        _connected_port = port
        _target = (host, port, client_id)
        return True
    except Exception:
        return False


def disconnect() -> None:
    global _connected_port, _target
    _target = None
    if ibkr.isConnected():
        ibkr.disconnect()
    _connected_port = None


async def supervise() -> None:
    global reconnecting
    delay = 1.0
    while True:
        await asyncio.sleep(delay if reconnecting else 1.0)
        if _target is None or ibkr.isConnected():
            reconnecting, delay = False, 1.0
            continue
        reconnecting = True
        if await connect(*_target):
            reconnecting, delay = False, 1.0
        else:
            delay = min(delay * 2, RECONNECT_MAX_DELAY)


def get_status() -> dict:
    # ib_async reports connected before connectAsync() finishes its initial
    # sync; only report it once connect() has recorded the port.
    connected = ibkr.isConnected() and _connected_port is not None
    port = _connected_port if connected else None
    settings = get_settings()
    mode = {settings.ibkr_paper_port: "paper", settings.ibkr_live_port: "live"}.get(port)
    return {
        "connected": connected,
        "port": port,
        "mode": mode,
        "server_version": ibkr.client.serverVersion() if connected else None,
    }


async def get_account_summary() -> dict:
    if not ibkr.isConnected():
        return {}

    tags = [
        "NetLiquidation",
        "UnrealizedPnL",
        "RealizedPnL",
        "BuyingPower",
        "TotalCashValue",
        "GrossPositionValue",
    ]
    # accountSummaryAsync() subscribes on first call and then serves the live,
    # continuously-updated values (reqAccountSummaryAsync() itself returns None).
    summary = await ibkr.accountSummaryAsync()
    result: dict[str, float] = {}
    for item in summary:
        # P&L arrives as per-currency ledger rows ("$LEDGER-UnrealizedPnL", or
        # "UnrealizedPnL" when TWS's "$LEDGER" prefix option is off); prefer the
        # BASE-currency total over individual currencies.
        tag = item.tag.removeprefix("$LEDGER-")
        if tag not in tags or (tag in result and item.currency != "BASE"):
            continue
        try:
            result[tag] = float(item.value)
        except ValueError:
            continue
    return result


async def get_positions() -> list[dict]:
    if not ibkr.isConnected():
        return []

    positions = await ibkr.reqPositionsAsync()
    result = []
    for pos in positions:
        contract = pos.contract
        result.append(
            {
                "symbol": contract.symbol,
                "asset_class": contract.secType,
                "currency": contract.currency,
                "quantity": pos.position,
                "avg_cost": pos.avgCost,
                "market_price": 0.0,
                "market_value": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
            }
        )

    # Enrich with market data
    if result:
        contracts = [pos.contract for pos in positions]
        try:
            tickers = await ibkr.reqTickersAsync(*contracts)
            for i, ticker in enumerate(tickers):
                if ticker and ticker.last and ticker.last > 0:
                    result[i]["market_price"] = ticker.last
                    result[i]["market_value"] = ticker.last * result[i]["quantity"]
                    result[i]["unrealized_pnl"] = (
                        ticker.last - result[i]["avg_cost"]
                    ) * result[i]["quantity"]
        except Exception:
            pass

    return result


def _bar_time(value) -> float:
    # Intraday bars carry a datetime; daily and longer bars carry a plain date,
    # which becomes midnight UTC so charts get one consistent unix-seconds axis.
    if isinstance(value, datetime):
        return value.timestamp()
    return float(calendar.timegm(value.timetuple()))


async def get_historical_bars(
    symbol: str,
    duration: str = "1 D",
    bar_size: str = "5 mins",
    what_to_show: str = "TRADES",
) -> list[dict]:
    if not ibkr.isConnected():
        return []

    contract = Stock(symbol, "SMART", "USD")
    await ibkr.qualifyContractsAsync(contract)

    bars = await ibkr.reqHistoricalDataAsync(
        contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=True,
        formatDate=1,
    )

    return [
        {
            "time": _bar_time(bar.date),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in bars
    ]
