import asyncio
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from backend.signals.config import SignalSettings, save_signal_settings
from backend.signals.rules import TRIGGERS
from backend.signals.service import signal_service

router = APIRouter()

EDITABLE = set(SignalSettings.model_fields) - {"symbol"}


@router.get("/state")
async def get_state():
    return signal_service.snapshot()


@router.get("/history")
async def get_history(
    limit: int = Query(default=100, ge=1, le=100),
    type: Optional[str] = None,
    before: Optional[str] = None,
):
    if type is not None and type not in {t.signal_type for t in TRIGGERS}:
        raise HTTPException(status_code=422, detail=f"Unknown signal type: {type}")
    try:
        return await signal_service.history_page(limit, type, before)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid cursor")


@router.put("/settings")
async def update_settings(values: dict[str, Any]):
    unknown = set(values) - EDITABLE
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown settings: {', '.join(sorted(unknown))}")
    try:
        settings = save_signal_settings(values)
    except ValidationError as e:
        first = e.errors()[0]
        raise HTTPException(status_code=422, detail=f"{first['loc'][0]}: {first['msg']}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    signal_service.apply_settings(settings)
    return settings.model_dump()


@router.websocket("/ws")
async def signals_ws(websocket: WebSocket):
    await websocket.accept()
    queue = signal_service.subscribe()

    async def forward():
        while True:
            await websocket.send_json(await queue.get())

    sender = asyncio.create_task(forward())
    try:
        await websocket.send_json({"type": "init", **signal_service.snapshot()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        signal_service.unsubscribe(queue)
