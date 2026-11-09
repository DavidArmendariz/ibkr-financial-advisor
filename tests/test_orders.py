import asyncio
import re
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from ib_async import CommissionReport, Execution, Fill, Option, Order, OrderStatus, Stock, Trade
from ib_async.util import UNSET_DOUBLE

from backend import database
from backend.routers import orders as orders_router
from backend.services import ibkr_service as svc

ORDER_WRITES = re.compile(r"\b(placeOrder|cancelOrder|reqGlobalCancel|reqAutoOpenOrders)\b")


class FakeIB:
    def __init__(self, trades=(), hang=False):
        self.trades = list(trades)
        self.replies = []
        self.stored = []
        self.hang = hang
        self.active = 0
        self.max_active = 0

    def isConnected(self):
        return True

    async def reqExecutionsAsync(self, execFilter=None):
        self.exec_filter = execFilter
        if self.hang:
            await asyncio.sleep(3600)
        return self.replies

    def fills(self):
        return self.stored

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


def test_only_the_broker_writes_orders():
    # Order entry sends orders from one module, behind a confirmed review; nothing else may.
    backend = Path(__file__).parent.parent / "backend"
    broker = backend / "trading" / "broker.py"
    offenders = [str(p) for p in backend.rglob("*.py") if p != broker and ORDER_WRITES.search(p.read_text())]
    assert offenders == []
    assert ORDER_WRITES.search(broker.read_text())


def test_the_main_connection_stays_read_only():
    source = (Path(__file__).parent.parent / "backend" / "services" / "ibkr_service.py").read_text()
    assert "readonly=True" in source and "readonly=False" not in source


def test_order_write_scan_catches_a_placement():
    assert ORDER_WRITES.search("await ibkr.placeOrder(contract, order)")


def fill(perm=7, shares=700.0, price=48.49, minute=39, side="SLD", commission=0.0, pnl=0.0, contract=None, exec_id="e1"):
    when = datetime(2026, 11, 2, 3, minute, tzinfo=timezone.utc)
    execution = Execution(execId=exec_id, permId=perm, side=side, shares=shares, price=price, exchange="OVERNIGHT", time=when)
    return Fill(contract or Stock("SOXS", "SMART", "USD"), execution, CommissionReport(commission=commission, realizedPNL=pnl), when)


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    state = SimpleNamespace(mode="live")
    monkeypatch.setattr(svc, "get_status", lambda: {"connected": True, "mode": state.mode})
    yield state
    await database._engine.dispose()


async def test_a_fill_becomes_a_filled_order(install, db):
    ib = install(FakeIB())
    ib.replies = [fill()]
    result = await svc.get_filled_orders()
    order = result["orders"][0]
    assert result["available"] is True and ib.exec_filter.time
    assert (order["symbol"], order["action"], order["quantity"]) == ("SOXS", "SELL", 700.0)
    assert (order["average_price"], order["venue"]) == (48.49, "OVERNIGHT")
    assert (order["commission"], order["realized_pnl"]) == (None, None)


async def test_parts_of_one_order_combine_with_a_weighted_price(install, db):
    install(FakeIB()).replies = [
        fill(shares=100, price=10.0, minute=1, commission=1.0, pnl=5.0, exec_id="a"),
        fill(shares=300, price=20.0, minute=9, commission=2.0, exec_id="b"),
    ]
    orders = (await svc.get_filled_orders())["orders"]
    assert len(orders) == 1
    assert orders[0]["quantity"] == 400 and orders[0]["average_price"] == 17.5
    assert (orders[0]["commission"], orders[0]["realized_pnl"]) == (3.0, 5.0)
    assert orders[0]["time"].startswith("2026-11-02T03:09")


async def test_commission_comes_from_the_stored_fill_not_the_blank_reply(install, db):
    ib = install(FakeIB())
    ib.replies = [fill()]
    ib.stored = [fill(commission=2.87, pnl=108.0)]
    order = (await svc.get_filled_orders())["orders"][0]
    assert (order["commission"], order["realized_pnl"]) == (2.87, 108.0)


async def test_unset_commission_is_empty(install, db):
    install(FakeIB()).replies = [fill(commission=UNSET_DOUBLE, pnl=UNSET_DOUBLE)]
    order = (await svc.get_filled_orders())["orders"][0]
    assert order["commission"] is None and order["realized_pnl"] is None


async def test_filled_orders_are_newest_first(install, db):
    install(FakeIB()).replies = [fill(perm=1, minute=1, side="BOT", exec_id="a"), fill(perm=2, minute=30, exec_id="b")]
    orders = (await svc.get_filled_orders())["orders"]
    assert [o["perm_id"] for o in orders] == [2, 1] and orders[1]["action"] == "BUY"


async def test_fills_timeout_is_reported_as_unavailable(install, db, monkeypatch):
    install(FakeIB(hang=True))
    monkeypatch.setattr(svc, "OPEN_ORDERS_TIMEOUT", 0.01)
    assert await svc.get_filled_orders() == {"available": False, "orders": []}


async def test_filled_endpoint_requires_connection(monkeypatch):
    monkeypatch.setattr(orders_router.ibkr_service.ibkr, "isConnected", lambda: False)
    with pytest.raises(HTTPException):
        await orders_router.get_filled_orders()


async def test_saved_fills_outlast_ibkrs_window(install, db):
    ib = install(FakeIB())
    ib.replies = [fill()]
    await svc.get_filled_orders()
    ib.replies = []
    assert len((await svc.get_filled_orders())["orders"]) == 1


async def test_saved_fills_survive_a_timeout(install, db, monkeypatch):
    ib = install(FakeIB())
    ib.replies = [fill()]
    await svc.get_filled_orders()
    ib.hang = True
    monkeypatch.setattr(svc, "OPEN_ORDERS_TIMEOUT", 0.01)
    result = await svc.get_filled_orders()
    assert result["available"] is False and len(result["orders"]) == 1


async def test_the_same_fill_counts_once(install, db):
    install(FakeIB()).replies = [fill()]
    await svc.get_filled_orders()
    order = (await svc.get_filled_orders())["orders"][0]
    assert order["quantity"] == 700


async def test_a_late_commission_is_saved_and_a_blank_reply_keeps_it(install, db):
    ib = install(FakeIB())
    ib.replies = [fill()]
    await svc.get_filled_orders()
    ib.stored = [fill(commission=2.87, pnl=107.0)]
    await svc.get_filled_orders()
    ib.stored = []
    order = (await svc.get_filled_orders())["orders"][0]
    assert (order["commission"], order["realized_pnl"]) == (2.87, 107.0)


async def test_live_and_paper_stay_apart(install, db):
    ib = install(FakeIB())
    ib.replies = [fill()]
    await svc.get_filled_orders()
    db.mode, ib.replies = "paper", []
    assert (await svc.get_filled_orders())["orders"] == []
    db.mode = "live"
    assert len((await svc.get_filled_orders())["orders"]) == 1


async def test_no_mode_saves_nothing(install, db):
    install(FakeIB()).replies = [fill()]
    db.mode = None
    assert await svc.sync_fills() is False
