import asyncio

from backend.config import get_settings
from backend.routers import connection
from backend.services import ibkr_service as svc
from tests.test_reconnect import FakeIB


def install(monkeypatch, listening):
    ib = FakeIB(listening)
    monkeypatch.setattr(svc, "ibkr", ib)
    monkeypatch.setattr(svc, "_connect_lock", asyncio.Lock())
    monkeypatch.setattr(svc, "_connected_port", None)
    monkeypatch.setattr(svc, "_target", None)
    return ib


async def test_auto_connect_uses_paper(monkeypatch):
    settings = get_settings()
    ib = install(monkeypatch, [settings.ibkr_paper_port, settings.ibkr_live_port])

    result = await connection.auto_connect()

    assert result == {"connected": True, "port": settings.ibkr_paper_port, "mode": "paper"}
    assert ib.calls == [("connect", settings.ibkr_paper_port)]


async def test_auto_connect_never_falls_back_to_live(monkeypatch):
    settings = get_settings()
    ib = install(monkeypatch, [settings.ibkr_live_port])

    result = await connection.auto_connect()

    assert result == {"connected": False, "port": None, "mode": None}
    assert ("connect", settings.ibkr_live_port) not in ib.calls
