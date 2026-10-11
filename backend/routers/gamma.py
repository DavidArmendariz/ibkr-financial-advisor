from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from backend.gamma.config import GammaSettings, save_gamma_settings
from backend.gamma.service import gamma_service

router = APIRouter()

EDITABLE = set(GammaSettings.model_fields) - {"symbol"}


@router.get("/state")
async def get_state():
    return gamma_service.state()


@router.post("/refresh")
async def refresh():
    gamma_service.trigger()
    return gamma_service.state()


@router.put("/settings")
async def update_settings(values: dict[str, Any]):
    unknown = set(values) - EDITABLE
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown settings: {', '.join(sorted(unknown))}")
    try:
        settings = save_gamma_settings(values)
    except ValidationError as e:
        first = e.errors()[0]
        raise HTTPException(status_code=422, detail=f"{first['loc'][0]}: {first['msg']}")
    gamma_service.trigger()
    return settings.model_dump()
