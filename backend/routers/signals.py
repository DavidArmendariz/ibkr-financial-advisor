import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from backend.signals.config import SignalSettings, save_signal_settings
from backend.signals.service import signal_service

router = APIRouter()

EDITABLE = set(SignalSettings.model_fields) - {"symbol"}


@router.get("/state")
async def get_state():
    return signal_service.snapshot()


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
