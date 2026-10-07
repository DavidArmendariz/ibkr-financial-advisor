import asyncio

import pytest

from backend.services import ibkr_service as svc

PAPER = ("127.0.0.1", 7497, 1)
LIVE = ("127.0.0.1", 7496, 1)


class FakeIB:
    def __init__(self, listening):
        self.listening = set(listening)
        self.port = None
        self.calls = []

    def isConnected(self):
        return self.port is not None

    async def connectAsync(self, host, port, clientId, timeout, readonly):
        self.calls.append(("connect", port))
        await asyncio.sleep(0.01)
        if port not in self.listening:
            raise ConnectionRefusedError
        self.port = port

    def disconnect(self):
        self.calls.append(("disconnect", self.port))
        self.port = None


@pytest.fixture
def fake(monkeypatch):
    def install(listening, target):
        ib = FakeIB(listening)
        monkeypatch.setattr(svc, "ibkr", ib)
        monkeypatch.setattr(svc, "_connect_lock", asyncio.Lock())
        monkeypatch.setattr(svc, "_connected_port", None)
        monkeypatch.setattr(svc, "_target", target)
        return ib

    return install


async def test_stale_retry_does_not_drop_a_newer_manual_connect(fake):
    # TWS switched from paper to live: the supervisor still targets paper when
    # the user clicks Live, and its queued retry must not undo that connection.
    ib = fake(listening={7496}, target=PAPER)
    manual = asyncio.create_task(svc.connect(*LIVE))
    await asyncio.sleep(0)
    retry = asyncio.create_task(svc.reconnect())
    assert await manual
    await retry
    assert ib.port == 7496
    assert ("disconnect", 7496) not in ib.calls
    assert svc._target == LIVE


async def test_reconnect_restores_dropped_connection(fake):
    ib = fake(listening={7497}, target=PAPER)
    assert await svc.reconnect()
    assert ib.port == 7497


async def test_reconnect_does_nothing_after_explicit_disconnect(fake):
    ib = fake(listening={7497}, target=None)
    assert await svc.reconnect()
    assert ib.calls == []
