import asyncio
from typing import Optional
from ib_insync import IB, util, Stock, Forex

# Patch asyncio so ib_insync works inside an existing event loop (FastAPI's)
util.patchAsyncio()

ibkr = IB()

_connected_port: Optional[int] = None


async def connect(host: str, port: int, client_id: int) -> bool:
    global _connected_port
    if ibkr.isConnected():
        if _connected_port == port:
            return True
        ibkr.disconnect()

    try:
        await ibkr.connectAsync(host, port, clientId=client_id, timeout=5)
        _connected_port = port
        return True
    except Exception:
        return False


def disconnect() -> None:
    global _connected_port
    if ibkr.isConnected():
        ibkr.disconnect()
    _connected_port = None


def get_status() -> dict:
    return {
        "connected": ibkr.isConnected(),
        "port": _connected_port,
        "server_version": ibkr.serverVersion() if ibkr.isConnected() else None,
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
    summary = await ibkr.reqAccountSummaryAsync()
    return {item.tag: float(item.value) for item in summary if item.tag in tags}


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
            "time": bar.date.timestamp() if hasattr(bar.date, "timestamp") else int(bar.date),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in bars
    ]
