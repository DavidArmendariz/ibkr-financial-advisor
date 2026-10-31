import asyncio
import re
from pathlib import Path

import pytest
from fastapi import HTTPException
from ib_async import Option, Order, OrderStatus, Stock, Trade
from ib_async.util import UNSET_DOUBLE

from backend.routers import orders as orders_router
from backend.services import ibkr_service as svc

ORDER_WRITES = re.compile(r"\b(placeOrder|cancelOrder|reqGlobalCancel|reqAutoOpenOrders)\b")


class FakeIB:
    def __init__(self, trades=(), hang=False):
        self.trades = list(trades)
        self.hang = hang
        self.active = 0
        self.max_active = 0

    def isConnected(self):
        return True

    async def reqAllOpenOrdersAsync(self):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(3600 if self.hang else 0.01)
            return self.trades
        finally:
            self.active -= 1


def trade(contract=None, status="PreSubmitted", **order):
    defaults = dict(permId=1, action="BUY", orderType="LMT", totalQuantity=100, lmtPrice=70.0, auxPrice=0.0, tif="DAY")
    return Trade(
        contract or Stock("SOXL", "SMART", "USD"),
        Order(**{**defaults, **order}),
        OrderStatus(status=status, filled=0, remaining=100),
    )


@pytest.fixture
def install(monkeypatch):
    def _install(ib):
        monkeypatch.setattr(svc, "ibkr", ib)
        monkeypatch.setattr(svc, "_open_orders_lock", asyncio.Lock())
        return ib

    return _install


async def test_stock_limit_order(install):
    install(FakeIB([trade()]))
    result = await svc.get_open_orders()
    assert result["available"] is True
    order = result["orders"][0]
    assert (order["perm_id"], order["symbol"], order["asset_class"]) == (1, "SOXL", "STK")
    assert (order["action"], order["order_type"], order["time_in_force"]) == ("BUY", "LMT", "DAY")
    assert (order["quantity"], order["filled"], order["remaining"]) == (100, 0, 100)
    assert (order["limit_price"], order["stop_price"]) == (70.0, None)
    assert (order["expiry"], order["strike"], order["right"]) == (None, None, None)
    assert order["status"] == "PreSubmitted"


async def test_option_order_keeps_contract_terms(install):
    install(FakeIB([trade(Option("SOXL", "20261218", 80.0, "C", "SMART"))]))
    order = (await svc.get_open_orders())["orders"][0]
    assert (order["expiry"], order["strike"], order["right"]) == ("20261218", 80.0, "C")


async def test_stock_right_placeholder_from_tws_is_dropped(install):
    contract = Stock("SOXL", "SMART", "USD")
    contract.right = "?"
    install(FakeIB([trade(contract)]))
    assert (await svc.get_open_orders())["orders"][0]["right"] is None


async def test_market_order_has_no_prices(install):
    install(FakeIB([trade(orderType="MKT", lmtPrice=UNSET_DOUBLE, auxPrice=UNSET_DOUBLE)]))
    order = (await svc.get_open_orders())["orders"][0]
    assert (order["limit_price"], order["stop_price"]) == (None, None)


async def test_stop_order_keeps_stop_price(install):
    install(FakeIB([trade(orderType="STP", lmtPrice=0.0, auxPrice=40.0)]))
    order = (await svc.get_open_orders())["orders"][0]
    assert (order["limit_price"], order["stop_price"]) == (None, 40.0)


async def test_manual_orders_sharing_order_id_stay_separate(install):
    install(FakeIB([trade(permId=1, orderId=0, clientId=0), trade(permId=2, orderId=0, clientId=0)]))
    assert [o["perm_id"] for o in (await svc.get_open_orders())["orders"]] == [1, 2]


async def test_order_sent_twice_is_listed_once(install):
    t = trade()
    install(FakeIB([t, t]))
    assert len((await svc.get_open_orders())["orders"]) == 1


@pytest.mark.parametrize(
    ("status", "listed"),
    [("PendingCancel", True), ("Inactive", True), ("Filled", False), ("Cancelled", False)],
)
async def test_only_finished_orders_are_removed(install, status, listed):
    install(FakeIB([trade(status=status)]))
    assert bool((await svc.get_open_orders())["orders"]) is listed


async def test_timeout_is_reported_as_unavailable(install, monkeypatch):
    install(FakeIB(hang=True))
    monkeypatch.setattr(svc, "OPEN_ORDERS_TIMEOUT", 0.01)
    assert await svc.get_open_orders() == {"available": False, "orders": []}


async def test_no_orders_is_available_and_empty(install):
    install(FakeIB())
    assert await svc.get_open_orders() == {"available": True, "orders": []}


async def test_overlapping_calls_run_one_at_a_time(install):
    ib = install(FakeIB([trade()]))
    await asyncio.gather(svc.get_open_orders(), svc.get_open_orders())
    assert ib.max_active == 1


async def test_endpoint_requires_connection(monkeypatch):
    monkeypatch.setattr(svc.ibkr, "isConnected", lambda: False)
    with pytest.raises(HTTPException) as err:
        await orders_router.get_open_orders()
    assert err.value.status_code == 503


def test_backend_never_writes_orders():
    backend = Path(__file__).parent.parent / "backend"
    offenders = [str(p) for p in backend.rglob("*.py") if ORDER_WRITES.search(p.read_text())]
    assert offenders == []


def test_order_write_scan_catches_a_placement():
    assert ORDER_WRITES.search("await ibkr.placeOrder(contract, order)")
