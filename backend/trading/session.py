import asyncio
import logging
from typing import Callable, Optional

from ib_async import IB

from backend.config import get_settings
from backend.services import ibkr_service

log = logging.getLogger(__name__)

CLIENT_ID_OFFSET = 20
CONNECT_TIMEOUT = 10


class TradingSessionError(Exception):
    pass


class TradingSession:
    # A second, order-capable API session. The app's main connection stays
    # read-only; this one opens only to send, change, or watch orders.
    def __init__(self, factory: Callable[[], IB] = IB) -> None:
        self._factory = factory
        self.ib: Optional[IB] = None
        self.port: Optional[int] = None
        self.account: Optional[str] = None
        self._lock = asyncio.Lock()
        self.on_connect: list[Callable[[IB], None]] = []

    def main_identity(self) -> tuple[int, str, str]:
        status = ibkr_service.get_status()
        if not status["connected"]:
            raise TradingSessionError("Not connected to IBKR.")
        accounts = ibkr_service.ibkr.managedAccounts()
        if len(accounts) != 1:
            raise TradingSessionError("The connected login has several accounts; order entry supports a single account.")
        return status["port"], status["mode"], accounts[0]

    def connected(self) -> bool:
        return self.ib is not None and self.ib.isConnected()

    async def ensure(self) -> IB:
        port, _, account = self.main_identity()
        async with self._lock:
            if self.connected() and (self.port != port or self.account != account):
                self.close()
            if not self.connected():
                ib = self._factory()
                settings = get_settings()
                try:
                    await ib.connectAsync(
                        settings.ibkr_host, port, clientId=settings.ibkr_client_id + CLIENT_ID_OFFSET, timeout=CONNECT_TIMEOUT, readonly=False
                    )
                except Exception as e:
                    raise TradingSessionError(f"Couldn't open the trading session ({type(e).__name__}).") from None
                accounts = ib.managedAccounts()
                if accounts != [account]:
                    ib.disconnect()
                    raise TradingSessionError("The trading session's account doesn't match the main connection's.")
                self.ib, self.port, self.account = ib, port, account
                for callback in self.on_connect:
                    callback(ib)
            return self.ib

    def close(self) -> None:
        if self.ib is not None and self.ib.isConnected():
            self.ib.disconnect()
        self.ib = None
        self.port = None
        self.account = None
