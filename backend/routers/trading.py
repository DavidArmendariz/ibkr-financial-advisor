from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from backend.trading import service
from backend.trading.broker import TradingError
from backend.trading.config import TradingSettings, save_trading_settings
from backend.trading.orders import SYMBOLS, Plan

router = APIRouter()


class PlanRequest(BaseModel):
    symbol: Literal["SOXL", "SOXS"]
    direction: Literal["long", "short"]
    shares: int = Field(gt=0, le=1_000_000)
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)


class ConfirmRequest(BaseModel):
    token: str = Field(min_length=10, max_length=100)


class ModifyRequest(BaseModel):
    role: Literal["stop", "target"]
    price: float = Field(gt=0)


def _error(e: TradingError) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"detail": e.message, "problems": e.problems})


@router.get("/state")
async def get_state():
    return await service.state()


@router.get("/bars/{symbol}")
async def get_bars(symbol: str):
    if symbol not in SYMBOLS:
        raise HTTPException(status_code=422, detail="Only SOXL and SOXS")
    return {"symbol": symbol, "bars": await service.chart_bars(symbol)}


@router.post("/review")
async def review(req: PlanRequest):
    try:
        return await service.broker.review(Plan(**req.model_dump()))
    except TradingError as e:
        return _error(e)


@router.post("/confirm")
async def confirm(req: ConfirmRequest):
    try:
        return await service.broker.confirm(req.token)
    except TradingError as e:
        return _error(e)


@router.post("/brackets/{bracket_id}/review-modify")
async def review_modify(bracket_id: str, req: ModifyRequest):
    try:
        return await service.broker.review_modify(bracket_id, req.role, req.price)
    except TradingError as e:
        return _error(e)


@router.post("/brackets/{bracket_id}/review-cancel")
async def review_cancel(bracket_id: str):
    try:
        return await service.broker.review_cancel(bracket_id)
    except TradingError as e:
        return _error(e)


@router.put("/settings")
async def update_settings(values: dict[str, Any]):
    unknown = set(values) - set(TradingSettings.model_fields)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown settings: {', '.join(sorted(unknown))}")
    try:
        return save_trading_settings(values).model_dump()
    except ValidationError as e:
        first = e.errors()[0]
        raise HTTPException(status_code=422, detail=f"{first['loc'][0]}: {first['msg']}")
