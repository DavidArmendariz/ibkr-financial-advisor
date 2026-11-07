from fastapi import APIRouter, HTTPException

from backend.services import ibkr_service

router = APIRouter()


@router.get("/filled")
async def get_filled_orders():
    if not ibkr_service.ibkr.isConnected():
        raise HTTPException(status_code=503, detail="Not connected to TWS")
    return await ibkr_service.get_filled_orders()


@router.get("/open")
async def get_open_orders():
    if not ibkr_service.ibkr.isConnected():
        raise HTTPException(status_code=503, detail="Not connected to TWS")
    return await ibkr_service.get_open_orders()
