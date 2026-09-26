import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import select

from backend.database import AsyncSessionLocal, ChatMessage, ChatThread, get_session
from backend.services import ai_service, ibkr_service

router = APIRouter()


# ── REST endpoints for thread management ──────────────────────────────────────

@router.get("/threads")
async def list_threads(session=Depends(get_session)):
    result = await session.exec(
        select(ChatThread).order_by(ChatThread.updated_at.desc())
    )
    return result.all()


class CreateThreadRequest(BaseModel):
    title: str = "New Chat"


@router.post("/threads")
async def create_thread(req: CreateThreadRequest, session=Depends(get_session)):
    thread = ChatThread(title=req.title)
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    return thread


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, session=Depends(get_session)):
    thread = await session.get(ChatThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    msgs_result = await session.exec(
        select(ChatMessage).where(ChatMessage.thread_id == thread_id)
    )
    for msg in msgs_result.all():
        await session.delete(msg)
    await session.delete(thread)
    await session.commit()
    return {"deleted": True}


@router.get("/threads/{thread_id}/messages")
async def get_messages(thread_id: str, session=Depends(get_session)):
    thread = await session.get(ChatThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    result = await session.exec(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.all()


# ── WebSocket streaming chat ───────────────────────────────────────────────────

@router.websocket("/ws/{thread_id}")
async def websocket_chat(thread_id: str, websocket: WebSocket):
    await websocket.accept()

    async with AsyncSessionLocal() as session:
        thread = await session.get(ChatThread, thread_id)
        if not thread:
            await websocket.send_json({"type": "error", "content": "Thread not found"})
            await websocket.close()
            return

        try:
            while True:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                user_text = data.get("message", "").strip()
                if not user_text:
                    continue

                # Auto-title thread on first user message (query before adding new msg)
                existing_result = await session.exec(
                    select(ChatMessage).where(ChatMessage.thread_id == thread_id)
                )
                if len(existing_result.all()) == 0:
                    thread.title = user_text[:60] + ("…" if len(user_text) > 60 else "")

                # Persist user message
                user_msg = ChatMessage(
                    thread_id=thread_id, role="user", content=user_text
                )
                session.add(user_msg)
                thread.updated_at = datetime.now(timezone.utc)
                await session.commit()

                # Build message history for Claude (reload after commit)
                history_result = await session.exec(
                    select(ChatMessage)
                    .where(ChatMessage.thread_id == thread_id)
                    .order_by(ChatMessage.created_at.asc())
                )
                history = [
                    {"role": m.role, "content": m.content}
                    for m in history_result.all()
                ]

                # Get live portfolio context
                portfolio: dict = {"summary": {}, "positions": []}
                if ibkr_service.ibkr.isConnected():
                    try:
                        portfolio["summary"] = await ibkr_service.get_account_summary()
                        portfolio["positions"] = await ibkr_service.get_positions()
                    except Exception:
                        pass

                # Stream AI response token by token
                assistant_text = ""
                await websocket.send_json({"type": "start"})

                async for chunk in ai_service.stream_chat_response(history, portfolio):
                    assistant_text += chunk
                    await websocket.send_json({"type": "chunk", "content": chunk})

                await websocket.send_json({"type": "done"})

                # Persist full assistant response
                assistant_msg = ChatMessage(
                    thread_id=thread_id, role="assistant", content=assistant_text
                )
                session.add(assistant_msg)
                thread.updated_at = datetime.now(timezone.utc)
                await session.commit()

        except WebSocketDisconnect:
            pass
        except Exception as e:
            try:
                await websocket.send_json({"type": "error", "content": str(e)})
            except Exception:
                pass
