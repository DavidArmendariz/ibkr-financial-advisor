from fastapi import APIRouter, HTTPException, Query

from backend.services import ibkr_service

router = APIRouter()


@router.get("/summary")
async def get_summary():
    if not ibkr_service.ibkr.isConnected():
        raise HTTPException(status_code=503, detail="Not connected to TWS")
    summary = await ibkr_service.get_account_summary()
    return summary


@router.get("/positions")
async def get_positions():
    if not ibkr_service.ibkr.isConnected():
        raise HTTPException(status_code=503, detail="Not connected to TWS")
    positions = await ibkr_service.get_positions()
    return positions


@router.get("/snapshot")
async def get_portfolio_snapshot():
    """Returns summary + positions in one call (used by the AI service for context)."""
    if not ibkr_service.ibkr.isConnected():
        return {"summary": {}, "positions": []}
    summary = await ibkr_service.get_account_summary()
    positions = await ibkr_service.get_positions()
    return {"summary": summary, "positions": positions}


@router.get("/chart/{symbol}")
async def get_chart_data(
    symbol: str,
    duration: str = Query(default="1 D", description="e.g. '1 D', '5 D', '1 M'"),
    bar_size: str = Query(default="5 mins", description="e.g. '1 min', '5 mins', '1 hour'"),
):
    if not ibkr_service.ibkr.isConnected():
        raise HTTPException(status_code=503, detail="Not connected to TWS")
    bars = await ibkr_service.get_historical_bars(symbol, duration, bar_size)
    return bars
