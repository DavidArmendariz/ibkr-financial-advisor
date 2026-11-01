from typing import Any

from fastapi import APIRouter, HTTPException

from backend.calendar_events.config import public_settings, save_calendar_settings
from backend.calendar_events.service import calendar_service

router = APIRouter()

TEXT_FIELDS = {"fred_api_key", "finnhub_api_key", "earnings_symbols"}
BOOL_FIELDS = {"alert_evening_enabled", "alert_soon_enabled"}


@router.get("")
async def get_calendar():
    return await calendar_service.state()


@router.put("/settings")
async def update_settings(values: dict[str, Any]):
    unknown = set(values) - TEXT_FIELDS - BOOL_FIELDS
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown settings: {', '.join(sorted(unknown))}")
    for key, value in values.items():
        if not isinstance(value, bool if key in BOOL_FIELDS else str):
            raise HTTPException(status_code=422, detail=f"Invalid value for {key}")
    clean = {k: v.strip() if isinstance(v, str) else v for k, v in values.items()}
    settings = save_calendar_settings(clean)
    if TEXT_FIELDS & set(values):
        calendar_service.refresh_now()
    return public_settings(settings)
