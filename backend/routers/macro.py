from fastapi import APIRouter

from backend.macro.service import macro_service

router = APIRouter()


@router.get("/state")
async def get_state():
    return macro_service.state()
