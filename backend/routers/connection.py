from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import get_settings
from backend.services import ibkr_service

router = APIRouter()


class ConnectRequest(BaseModel):
    mode: str = "paper"  # "paper" | "live"


@router.get("/status")
async def get_status():
    return ibkr_service.get_status()


@router.post("/connect")
async def connect(req: ConnectRequest):
    settings = get_settings()
    port = settings.ibkr_paper_port if req.mode == "paper" else settings.ibkr_live_port
    success = await ibkr_service.connect(settings.ibkr_host, port, settings.ibkr_client_id)
    return {"connected": success, "port": port, "mode": req.mode}


@router.post("/auto-connect")
async def auto_connect():
    """Try the paper port only. Keeps an existing connection as-is."""
    settings = get_settings()
    status = ibkr_service.get_status()
    if status["connected"]:
        return {"connected": True, "port": status["port"], "mode": status["mode"]}
    # Never fall back to live: connecting to a real-money account must be an explicit click.
    port = settings.ibkr_paper_port
    if await ibkr_service.connect(settings.ibkr_host, port, settings.ibkr_client_id):
        return {"connected": True, "port": port, "mode": "paper"}
    return {"connected": False, "port": None, "mode": None}


@router.post("/disconnect")
async def disconnect():
    ibkr_service.disconnect()
    return {"connected": False}
