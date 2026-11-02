from fastapi import APIRouter

from backend.global_markets.service import global_markets_service

router = APIRouter()


@router.get("")
async def get_state():
    return global_markets_service.state()
