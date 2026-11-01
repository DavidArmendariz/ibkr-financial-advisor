import asyncio
import calendar
from datetime import datetime
from typing import Optional
from ib_async import IB, Contract, OrderStatus, Stock, Forex
from ib_async.util import UNSET_DOUBLE

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
        # readonly: without it ib_async requests open and completed orders on every
        # connect, which TWS can reject (with a pop-up) when "Read-Only API" is
        # enabled. Open orders are read only on demand, while the Orders view is open.
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


async def reconnect() -> bool:
    target = _target
    async with _connect_lock:
        # Re-check under the lock: a manual connect (e.g. switching to live) may
        # have finished while this waited, and must not be undone.
        if target is None or target != _target or ibkr.isConnected():
            return True
        return await _connect(*target)


async def supervise() -> None:
    global reconnecting
    delay = 1.0
    while True:
        await asyncio.sleep(delay if reconnecting else 1.0)
        if _target is None or ibkr.isConnected():
            reconnecting, delay = False, 1.0
            continue
        reconnecting = True
        if await reconnect():
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


SNAPSHOT_TIMEOUT = 5.0


# A snapshot for a contract without a market data subscription (10168) never
# completes, so one unsubscribed position would hang the whole positions request.
async def _snapshot(contract: Contract):
    try:
        tickers = await asyncio.wait_for(ibkr.reqTickersAsync(contract), SNAPSHOT_TIMEOUT)
    except asyncio.TimeoutError:
        return None
    return tickers[0] if tickers else None


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
            tickers = await asyncio.gather(*(_snapshot(c) for c in contracts))
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


OPEN_ORDERS_TIMEOUT = 5.0

# ib_async tracks this request under one name, so a second concurrent call would
# replace the first one's future and leave it unanswered.
_open_orders_lock = asyncio.Lock()

# ActiveStates would hide PendingCancel, which can still fill, and DoneStates includes
# Inactive, which is an order the user needs to see.
_FINISHED_STATES = OrderStatus.DoneStates - {OrderStatus.Inactive}


def _order_price(value: Optional[float]) -> Optional[float]:
    return None if value in (None, 0, UNSET_DOUBLE) else value


def _open_order(trade) -> dict:
    contract, order, status = trade.contract, trade.order, trade.orderStatus
    return {
        "perm_id": order.permId,
        "symbol": contract.symbol,
        "asset_class": contract.secType,
        "currency": contract.currency,
        "expiry": contract.lastTradeDateOrContractMonth or None,
        "strike": contract.strike or None,
        # TWS sends "?" for a stock, where a right doesn't apply.
        "right": None if contract.right in ("", "?") else contract.right,
        "action": order.action,
        "order_type": order.orderType,
        "quantity": order.totalQuantity,
        "filled": status.filled,
        "remaining": status.remaining,
        "limit_price": _order_price(order.lmtPrice),
        "stop_price": _order_price(order.auxPrice),
        "time_in_force": order.tif,
        "status": status.status,
    }


async def get_open_orders() -> dict:
    async with _open_orders_lock:
        try:
            # TWS's refusal is only a warning to ib_async, so a request blocked by
            # Read-Only API never completes and has to be timed out.
            trades = await asyncio.wait_for(ibkr.reqAllOpenOrdersAsync(), OPEN_ORDERS_TIMEOUT)
        except asyncio.TimeoutError:
            return {"available": False, "orders": []}

    # TWS can send an order twice.
    unique = {id(trade): trade for trade in trades}.values()
    orders = [_open_order(t) for t in unique if t.orderStatus.status not in _FINISHED_STATES]
    return {"available": True, "orders": orders}


def _bar_time(value) -> float:
    # Intraday bars carry a datetime; daily and longer bars carry a plain date,
    # which becomes midnight UTC so charts get one consistent unix-seconds axis.
    if isinstance(value, datetime):
        return value.timestamp()
    return float(calendar.timegm(value.timetuple()))


async def get_historical_bars(
    symbol: str | Contract,
    duration: str = "1 D",
    bar_size: str = "5 mins",
    what_to_show: str = "TRADES",
    use_rth: bool = True,
    end: Optional[datetime] = None,
) -> list[dict]:
    if not ibkr.isConnected():
        return []

    if isinstance(symbol, Contract):
        contract = symbol
    else:
        contract = Stock(symbol, "SMART", "USD")
        await ibkr.qualifyContractsAsync(contract)

    bars = await ibkr.reqHistoricalDataAsync(
        contract,
        endDateTime=end or "",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=use_rth,
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
