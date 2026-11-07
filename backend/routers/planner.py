from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from backend.planner import calc
from backend.planner.config import PlannerSettings, get_planner_settings, save_planner_settings
from backend.planner.service import DAILY_ATR_PERIOD, SYMBOLS, planner_service
from backend.services import ibkr_service
from backend.signals.config import get_signal_settings

router = APIRouter()


class PlanRequest(BaseModel):
    symbol: Literal["SOXL", "SOXS"]
    atr_basis: Literal["intraday", "daily"]
    entry: Optional[float] = None
    stop_multiple: float
    target_multiple: float
    risk_mode: Literal["percent", "dollars"]
    risk_percent: float
    risk_dollars: float


async def _account() -> Optional[dict]:
    if not ibkr_service.ibkr.isConnected():
        return None
    summary = await ibkr_service.get_account_summary()
    return {"net_liquidation": summary.get("NetLiquidation"), "available_funds": summary.get("AvailableFunds")}


@router.get("")
async def get_planner():
    await planner_service.refresh(datetime.now(timezone.utc))
    status = ibkr_service.get_status()
    s = get_signal_settings()
    return {
        "connected": status["connected"],
        "mode": status["mode"],
        "account": await _account(),
        "settings": get_planner_settings().model_dump(),
        "intraday_minutes": s.timeframe_minutes,
        "intraday_period": s.atr_period,
        "daily_period": DAILY_ATR_PERIOD,
        "quotes": [planner_service.quote_state(symbol) for symbol in SYMBOLS],
    }


@router.put("/settings")
async def update_settings(values: dict[str, Any]):
    unknown = set(values) - set(PlannerSettings.model_fields)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown settings: {', '.join(sorted(unknown))}")
    try:
        return save_planner_settings(values).model_dump()
    except ValidationError as e:
        first = e.errors()[0]
        raise HTTPException(status_code=422, detail=f"{first['loc'][0]}: {first['msg']}")


@router.post("/plan")
async def make_plan(req: PlanRequest):
    q = planner_service.quote(req.symbol)
    account = await _account()
    atr = q.intraday_atr if req.atr_basis == "intraday" else q.daily_atr
    risk = calc.risk_amount(req.risk_mode, req.risk_percent, req.risk_dollars, account and account["net_liquidation"])
    # A buy fills at the ask, so that's the default entry when there's a quote.
    default_entry = q.ask if q.ask is not None else q.price
    return calc.plan(
        req.entry if req.entry is not None else default_entry,
        atr,
        req.stop_multiple,
        req.target_multiple,
        risk,
        account and account["available_funds"],
    )
