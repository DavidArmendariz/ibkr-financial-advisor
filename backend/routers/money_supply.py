from fastapi import APIRouter

from backend.money_supply.service import money_supply_service

router = APIRouter()


@router.get("")
async def get_money_supply():
    return await money_supply_service.state()
