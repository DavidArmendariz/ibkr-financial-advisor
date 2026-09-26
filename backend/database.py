from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Field

from backend.config import get_settings


class ChatThread(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    thread_id: str = Field(foreign_key="chatthread.id", index=True)
    role: str = Field(max_length=20)  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_engine = None
AsyncSessionLocal = None


def get_engine():
    global _engine, AsyncSessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
        AsyncSessionLocal = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _engine


async def create_db_and_tables():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
