from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import create_db_and_tables
from backend.routers import connection, portfolio, chat
from backend.services.ibkr_service import ibkr


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield
    if ibkr.isConnected():
        ibkr.disconnect()


app = FastAPI(title="IBKR Financial Advisor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "file://", "app://"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connection.router, prefix="/api/connection", tags=["connection"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
