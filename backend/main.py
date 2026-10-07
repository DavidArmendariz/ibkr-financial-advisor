import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import create_db_and_tables
from backend.routers import connection, portfolio, chat, settings, signals
from backend.services import ibkr_service
from backend.services.ibkr_service import ibkr
from backend.signals.service import signal_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # uvicorn runs its loop via asyncio.Runner(loop_factory=...), which doesn't
    # register it as the thread's current loop. ib_async looks the loop up with
    # get_event_loop(), so register it or its futures land on a different loop.
    asyncio.set_event_loop(asyncio.get_running_loop())
    await create_db_and_tables()
    supervisor = asyncio.create_task(ibkr_service.supervise())
    await signal_service.start()
    yield
    supervisor.cancel()
    await signal_service.stop()
    if ibkr.isConnected():
        ibkr.disconnect()


app = FastAPI(title="DeltaAdvisor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Vite dev server, and the packaged renderer served via Electron's app:// scheme
    allow_origins=["http://localhost:5273", "app://bundle"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connection.router, prefix="/api/connection", tags=["connection"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # Entry point for the frozen PyInstaller binary spawned by Electron in production
    import uvicorn

    # Open WebSockets and requests still waiting on IBKR can otherwise keep the
    # server from ever finishing its shutdown.
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=get_settings().backend_port,
        log_level="info",
        timeout_graceful_shutdown=5,
    )
