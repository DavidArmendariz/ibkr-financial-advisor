from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from backend.rotation.config import RotationSettings, save_rotation_settings
from backend.rotation.service import rotation_service

router = APIRouter()


@router.get("")
async def get_rotation():
    return rotation_service.state()


@router.put("/settings")
async def update_settings(values: dict[str, Any]):
    unknown = set(values) - set(RotationSettings.model_fields)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown settings: {', '.join(sorted(unknown))}")
    try:
        return save_rotation_settings(values).model_dump()
    except ValidationError as e:
        first = e.errors()[0]
        raise HTTPException(status_code=422, detail=f"{first['loc'][0]}: {first['msg']}")
