import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from ib_async import OrderStatus, Trade

from backend import database
from backend.database import TradeBracket, WatchedStop
from backend.services import ibkr_service
from backend.signals.sessions import ET, SessionCalendar
from backend.trading import broker as broker_module
from backend.trading import config as trading_config
from backend.trading import watcher as watcher_module
from backend.trading.broker import Broker, TradingError, parse_ref
from backend.trading.config import TradingSettings
from backend.trading.orders import Plan, build, capped_limit, problems
from backend.trading.session import TradingSession, TradingSessionError
from backend.trading.sessions import AFTER, CLOSED, OVERNIGHT, PRE, REGULAR, session_at
from backend.trading.watcher import Watcher, crossed

AFTER_HOURS = datetime(2026, 11, 9, 17, 0, tzinfo=ET)  # Monday
NIGHT = datetime(2026, 11, 9, 22, 0, tzinfo=ET)
LONG = Plan("SOXL", "long", 100, 46.0, 44.5, 49.0)
SHORT = Plan("SOXS", "short", 50, 20.0, 21.0, 18.0)


# ── Sessions ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "when,expected",
    [
        (datetime(2026, 11, 9, 3, 49, tzinfo=ET), OVERNIGHT),
        (datetime(2026, 11, 9, 3, 50, tzinfo=ET), CLOSED),
        (datetime(2026, 11, 9, 4, 0, tzinfo=ET), PRE),
        (datetime(2026, 11, 9, 9, 30, tzinfo=ET), REGULAR),
        (datetime(2026, 11, 9, 16, 0, tzinfo=ET), AFTER),
        (datetime(2026, 11, 9, 19, 59, tzinfo=ET), AFTER),
        (datetime(2026, 11, 9, 20, 0, tzinfo=ET), OVERNIGHT),
        (datetime(2026, 11, 6, 20, 0, tzinfo=ET), CLOSED),  # Friday night
        (datetime(2026, 11, 7, 12, 0, tzinfo=ET), CLOSED),  # Saturday
        (datetime(2026, 11, 8, 20, 0, tzinfo=ET), OVERNIGHT),  # Sunday night
    ],
)
def test_session_boundaries(when, expected):
    assert session_at(when) == expected


def test_half_day_after_hours_end_four_hours_after_the_early_close():
    cal = SessionCalendar.from_liquid_hours("20261127:0930-20261127:1300", "US/Eastern")
    assert session_at(datetime(2026, 11, 27, 13, 30, tzinfo=ET), cal) == AFTER
    assert session_at(datetime(2026, 11, 27, 17, 0, tzinfo=ET), cal) == CLOSED


def test_no_overnight_before_a_holiday():
    cal = SessionCalendar.from_liquid_hours("20261126:CLOSED", "US/Eastern")
    assert session_at(datetime(2026, 11, 25, 21, 0, tzinfo=ET), cal) == CLOSED


# ── Order building ───────────────────────────────────────────────────────────


def test_day_bracket_for_a_long_trade():
    p = build(LONG, AFTER, 1.0)
    entry, stop, target = p.orders
    assert (entry.action, entry.order_type, entry.limit_price, entry.exchange) == ("BUY", "LMT", 46.0, "SMART")
    assert (stop.action, stop.order_type, stop.stop_price, stop.limit_price) == ("SELL", "STP LMT", 44.5, 44.05)
    assert (target.action, target.order_type, target.limit_price) == ("SELL", "LMT", 49.0)
    assert all(o.outside_rth and o.tif == "GTC" for o in p.orders) and p.watched_stop is None


def test_short_bracket_has_the_stop_above_and_the_target_below():
    entry, stop, target = build(SHORT, REGULAR, 1.0).orders
    assert entry.action == "SELL" and stop.action == "BUY" and target.action == "BUY"
    assert stop.stop_price == 21.0 and stop.limit_price == 21.21 and target.limit_price == 18.0


def test_overnight_sends_the_entry_and_plans_the_rest():
    p = build(LONG, OVERNIGHT, 1.0)
    assert [(o.role, o.exchange, o.tif, o.outside_rth) for o in p.orders] == [("entry", "OVERNIGHT", "DAY", False)]
    assert [(o.role, o.exchange) for o in p.after_fill] == [("stop", "SMART"), ("target", "SMART"), ("target", "OVERNIGHT")]
    assert p.watched_stop == 44.5


def test_a_plain_stop_is_never_built():
    for session in (PRE, REGULAR, AFTER, OVERNIGHT):
        for plan in (LONG, SHORT):
            p = build(plan, session, 1.0)
            assert all(o.order_type in ("LMT", "STP LMT") for o in [*p.orders, *p.after_fill])


def test_gap_cap_rounds_toward_the_safe_side():
    assert capped_limit(44.5, "SELL", 1.0) == 44.05  # 44.055 rounds down for a sell
    assert capped_limit(21.0, "BUY", 1.0) == 21.21
    assert capped_limit(10.01, "BUY", 1.0) == 10.12  # 10.1101 rounds up for a buy


@pytest.mark.parametrize(
    "plan,mode,live,session,fragment",
    [
        (Plan("SOXL", "long", 100, 46, 47, 49), "paper", False, AFTER, "stop must be below"),
        (Plan("SOXL", "long", 100, 46, 45, 45.5), "paper", False, AFTER, "take profit must be above"),
        (Plan("SOXS", "short", 10, 20, 19, 18), "paper", False, AFTER, "stop must be above"),
        (Plan("SOXL", "long", 1000, 46, 45, 49), "paper", False, AFTER, "per-order cap"),
        (LONG, "live", False, AFTER, "Live trading is off"),
        (LONG, None, False, AFTER, "Not connected"),
        (LONG, "paper", False, CLOSED, "market is closed"),
        (Plan("TQQQ", "long", 1, 46, 45, 49), "paper", False, AFTER, "Only SOXL and SOXS"),
    ],
)
def test_refusals(plan, mode, live, session, fragment):
    assert any(fragment in p for p in problems(plan, session, mode, live, 25_000))


def test_live_is_allowed_once_switched_on():
    assert problems(LONG, AFTER, "live", True, 25_000) == []


def test_settings_validate_before_saving(monkeypatch):
    saved = {}
    monkeypatch.setattr(trading_config, "save_env_values", saved.update)
    trading_config.get_trading_settings.cache_clear()
    monkeypatch.delenv("TRADING_MAX_ORDER_VALUE", raising=False)
    with pytest.raises(Exception):
        trading_config.save_trading_settings({"max_order_value": -1})
    assert saved == {}
    trading_config.save_trading_settings({"live_enabled": True})
    assert saved == {"TRADING_LIVE_ENABLED": "true"}
    trading_config.get_trading_settings.cache_clear()


def test_live_trading_is_off_by_default():
    assert TradingSettings.model_fields["live_enabled"].default is False


# ── Fakes ────────────────────────────────────────────────────────────────────


class Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def emit(self, *args):
        for h in self.handlers:
            h(*args)


class FakeIB:
    def __init__(self, accounts=("DU123",)):
        self.accounts = list(accounts)
        self.connected = False
        self.placed, self.cancelled, self._trades = [], [], []
        self.orderStatusEvent, self.errorEvent = Event(), Event()
        self.next_id = 100
        self.connect_args = None
        self.tickers = {}

    async def connectAsync(self, host, port, clientId, timeout, readonly):
        self.connect_args = dict(port=port, clientId=clientId, readonly=readonly)
        self.connected = True

    def isConnected(self):
        return self.connected

    def disconnect(self):
        self.connected = False

    def managedAccounts(self):
        return self.accounts

    async def qualifyContractsAsync(self, contract):
        contract.conId = 73340487
        return [contract]

    async def whatIfOrderAsync(self, contract, order):
        return SimpleNamespace(commission=1.0, minCommission=None, maxCommission=None, initMarginChange=4600.0, warningText="")

    def placeOrder(self, contract, order):
        if not order.orderId:
            order.orderId = self.next_id
            self.next_id += 1
        trade = next((t for t in self._trades if t.order.orderId == order.orderId), None)
        if trade is None:
            trade = Trade(contract, order, OrderStatus(orderId=order.orderId, status="PreSubmitted"))
            self._trades.append(trade)
        self.placed.append((contract.exchange, order))
        return trade

    def cancelOrder(self, order):
        self.cancelled.append(order.orderId)

    def trades(self):
        return self._trades

    def reqMarketDataType(self, kind):
        pass

    def reqMktData(self, contract, *args):
        return self.tickers.setdefault(contract.symbol, SimpleNamespace(contract=contract, bid=float("nan"), ask=float("nan")))

    def cancelMktData(self, contract):
        pass


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    yield
    await database._engine.dispose()


@pytest.fixture
def world(db, monkeypatch):
    state = SimpleNamespace(connected=True, port=7497, mode="paper", accounts=["DU123"], now=AFTER_HOURS, notes=[], live=False)
    monkeypatch.setattr(ibkr_service, "get_status", lambda: {"connected": state.connected, "port": state.port if state.connected else None, "mode": state.mode if state.connected else None})
    monkeypatch.setattr(ibkr_service.ibkr, "managedAccounts", lambda: state.accounts)
    monkeypatch.setattr(broker_module, "get_trading_settings", lambda: TradingSettings.model_construct(live_enabled=state.live, max_order_value=25_000.0, gap_cap_percent=1.0))
    state.ib = FakeIB()
    state.session = TradingSession(factory=lambda: state.ib)
    state.broker = Broker(state.session, clock=lambda: state.now)
    state.broker.notify = lambda title, body: state.notes.append((title, body))
    return state


async def settle():
    for _ in range(5):
        await asyncio.sleep(0)


# ── Trading session ──────────────────────────────────────────────────────────


async def test_trading_session_is_separate_and_order_capable(world):
    ib = await world.session.ensure()
    assert ib.connect_args == {"port": 7497, "clientId": ib.connect_args["clientId"], "readonly": False}
    from backend.config import get_settings
    assert ib.connect_args["clientId"] == get_settings().ibkr_client_id + 20


async def test_trading_session_refuses_a_different_account(world):
    world.ib.accounts = ["DU999"]
    with pytest.raises(TradingSessionError, match="doesn't match"):
        await world.session.ensure()


async def test_trading_session_needs_the_main_connection(world):
    world.connected = False
    with pytest.raises(TradingSessionError, match="Not connected"):
        await world.session.ensure()


# ── Reviews and confirmation ─────────────────────────────────────────────────


async def test_review_sends_nothing_and_confirm_sends_the_bracket(world):
    review = await world.broker.review(LONG)
    assert world.ib.placed == []
    assert review["mode"] == "paper" and review["account"] == "DU123" and review["session"] == AFTER
    assert [o["role"] for o in review["orders"]] == ["entry", "stop", "target"]
    assert review["risk"] == 150.0 and review["reward"] == 300.0 and review["what_if"]["commission"] == 1.0
    record = await world.broker.confirm(review["token"])
    parent, stop, target = (o for _, o in world.ib.placed)
    assert parent.transmit is False and stop.transmit is False and target.transmit is True
    assert stop.parentId == parent.orderId and target.parentId == parent.orderId
    assert stop.ocaGroup == target.ocaGroup == f"DA-{record['id']}" and stop.orderType == "STP LMT" and stop.outsideRth
    assert parse_ref(stop.orderRef) == (record["id"], "stop")
    assert record["state"] == "working" and set(record["orders"]) == {"entry", "stop", "target"}


async def test_a_review_is_single_use(world):
    review = await world.broker.review(LONG)
    await world.broker.confirm(review["token"])
    with pytest.raises(TradingError, match="already used"):
        await world.broker.confirm(review["token"])
    assert len(world.ib.placed) == 3


async def test_a_review_expires_after_two_minutes(world):
    review = await world.broker.review(LONG)
    world.now += timedelta(seconds=121)
    with pytest.raises(TradingError, match="expired"):
        await world.broker.confirm(review["token"])
    assert world.ib.placed == []


async def test_a_changed_account_voids_the_review(world):
    review = await world.broker.review(LONG)
    world.mode, world.port = "live", 7496
    with pytest.raises(TradingError, match="account changed"):
        await world.broker.confirm(review["token"])
    assert world.ib.placed == []


async def test_live_is_refused_unless_switched_on(world):
    world.mode, world.port = "live", 7496
    with pytest.raises(TradingError, match="Live trading is off"):
        await world.broker.review(LONG)
    world.live = True
    review = await world.broker.review(LONG)
    assert review["mode"] == "live"


async def test_a_session_change_voids_the_review(world):
    world.now = datetime(2026, 11, 9, 19, 59, tzinfo=ET)
    review = await world.broker.review(LONG)
    world.now = datetime(2026, 11, 9, 20, 0, 30, tzinfo=ET)
    with pytest.raises(TradingError, match="session changed"):
        await world.broker.confirm(review["token"])


async def test_modify_moves_only_the_reviewed_order(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    before = len(world.ib.placed)
    review = await world.broker.review_modify(record["id"], "stop", 45.0)
    assert len(world.ib.placed) == before
    updated = await world.broker.confirm(review["token"])
    exchange, order = world.ib.placed[-1]
    assert order.orderType == "STP LMT" and order.auxPrice == 45.0 and order.lmtPrice == 44.55
    assert updated["stop"] == 45.0 and len(world.ib.placed) == before + 1


async def test_modify_refuses_a_stop_past_the_entry(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    with pytest.raises(TradingError, match="below the entry"):
        await world.broker.review_modify(record["id"], "stop", 47.0)


async def test_cancel_cancels_every_working_order(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    review = await world.broker.review_cancel(record["id"])
    assert review["warning"] is None
    cancelled = await world.broker.confirm(review["token"])
    assert len(world.ib.cancelled) == 3 and cancelled["state"] == "cancelled"


# ── Fills, rejections, and the overnight flow ────────────────────────────────


def status(trade, value):
    trade.orderStatus.status = value
    return trade


async def test_a_rejected_exit_after_the_fill_warns_the_position_is_unprotected(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    entry, stop, target = world.ib.trades()
    await world.broker.apply_status(record["id"], "entry", status(entry, "Filled"))
    world.broker._on_error(target.order.orderId, 201, "Order rejected - reason: price outside limits", None)
    await world.broker.apply_status(record["id"], "target", status(target, "Inactive"))
    saved = await world.broker.bracket_record(record["id"])
    assert saved["state"] == "open" and "no take profit" in saved["warning"]
    assert any("order problem" in t for t, _ in world.notes)


async def test_an_exit_fill_closes_the_bracket(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    entry, stop, target = world.ib.trades()
    await world.broker.apply_status(record["id"], "entry", status(entry, "Filled"))
    await world.broker.apply_status(record["id"], "target", status(target, "Filled"))
    assert (await world.broker.bracket_record(record["id"]))["state"] == "closed"


async def test_overnight_entry_fill_places_exits_and_a_watched_stop(world):
    world.now = NIGHT
    review = await world.broker.review(LONG)
    assert review["watched_stop"] == 44.5 and len(review["after_fill"]) == 3
    record = await world.broker.confirm(review["token"])
    assert [(ex, o.action) for ex, o in world.ib.placed] == [("OVERNIGHT", "BUY")]
    await world.broker.apply_status(record["id"], "entry", status(world.ib.trades()[0], "Filled"))
    placed = [(ex, o.orderType, o.action, o.ocaGroup) for ex, o in world.ib.placed[1:]]
    oca = f"DA-{record['id']}"
    assert placed == [("SMART", "STP LMT", "SELL", oca), ("SMART", "LMT", "SELL", oca), ("OVERNIGHT", "LMT", "SELL", oca)]
    saved = await world.broker.bracket_record(record["id"])
    assert saved["state"] == "open" and saved["watched_stop"]["level"] == 44.5 and saved["watched_stop"]["active"]


async def test_watched_stop_exit_cancels_the_target_and_sends_a_capped_limit(world, monkeypatch):
    monkeypatch.setattr(broker_module, "EXIT_FILL_SECONDS", 0)
    world.now = NIGHT
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    await world.broker.apply_status(record["id"], "entry", status(world.ib.trades()[0], "Filled"))
    overnight_target = world.ib.trades()[-1]
    await world.broker.trigger_stop(record["id"], 44.4, 44.45)
    assert overnight_target.order.orderId in world.ib.cancelled
    exchange, exit_order = world.ib.placed[-1]
    assert (exchange, exit_order.action, exit_order.lmtPrice, exit_order.tif) == ("OVERNIGHT", "SELL", 43.95, "DAY")
    assert any("stop hit" in t for t, _ in world.notes)
    await asyncio.sleep(0.01)
    assert any("not filled" in t for t, _ in world.notes)
    saved = await world.broker.bracket_record(record["id"])
    assert saved["watched_stop"]["active"] is False and saved["watched_stop"]["triggered_at"]


# ── Watcher ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "action,level,bid,ask,expected",
    [
        ("SELL", 44.5, 44.5, 44.6, True),
        ("SELL", 44.5, 44.51, 44.6, False),
        ("BUY", 21.0, 20.9, 21.0, True),
        ("BUY", 21.0, 20.9, 20.99, False),
        ("SELL", 44.5, float("nan"), 44.6, False),  # no book
        ("SELL", 44.5, 44.0, 43.9, False),  # crossed book
        ("SELL", 44.5, -1, 44.6, False),
    ],
)
def test_crossing_uses_the_book(action, level, bid, ask, expected):
    assert crossed(action, level, bid, ask) is expected


async def test_watcher_triggers_on_a_cross_and_records_gaps(world, monkeypatch):
    monkeypatch.setattr(broker_module, "EXIT_FILL_SECONDS", 3600)
    world.now = NIGHT
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    await world.broker.apply_status(record["id"], "entry", status(world.ib.trades()[0], "Filled"))
    w = Watcher(world.broker, clock=lambda: world.now)
    await w.tick()  # no quote yet: a gap opens
    gaps = (await world.broker.bracket_record(record["id"]))["watched_stop"]["gaps"]
    assert len(gaps) == 1 and gaps[0][1] is None
    world.ib.tickers["SOXL"].bid, world.ib.tickers["SOXL"].ask = 45.0, 45.05
    world.now += timedelta(seconds=5)
    await w.tick()
    saved = await world.broker.bracket_record(record["id"])
    assert saved["watched_stop"]["gaps"][0][1] is not None and "exit" not in saved["orders"]
    world.ib.tickers["SOXL"].bid = 44.4
    await w.tick()
    saved = await world.broker.bracket_record(record["id"])
    assert "exit" in saved["orders"] and saved["watched_stop"]["active"] is False
    for task in world.broker._exit_checks.values():
        task.cancel()


async def test_a_day_bracket_held_into_the_night_gets_overnight_protection(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    await world.broker.apply_status(record["id"], "entry", status(world.ib.trades()[0], "Filled"))
    world.now = NIGHT
    w = Watcher(world.broker, clock=lambda: world.now)
    await w.tick()
    await w.tick()
    overnight = [o for ex, o in world.ib.placed if ex == "OVERNIGHT"]
    assert len(overnight) == 1 and overnight[0].ocaGroup == f"DA-{record['id']}"
    assert (await world.broker.bracket_record(record["id"]))["watched_stop"]["active"]


async def test_watcher_does_nothing_outside_the_overnight_session(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    await world.broker.apply_status(record["id"], "entry", status(world.ib.trades()[0], "Filled"))
    before = len(world.ib.placed)
    await Watcher(world.broker, clock=lambda: world.now).tick()
    assert len(world.ib.placed) == before


async def test_a_restart_resumes_watched_stops_from_the_database(world):
    world.now = NIGHT
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    await world.broker.apply_status(record["id"], "entry", status(world.ib.trades()[0], "Filled"))
    fresh = Broker(world.session, clock=lambda: world.now)
    w = Watcher(fresh, clock=lambda: world.now)
    await w.tick()
    world.ib.tickers["SOXL"].bid, world.ib.tickers["SOXL"].ask = 44.0, 44.1
    await w.tick()
    assert "exit" in (await fresh.bracket_record(record["id"]))["orders"]
    for task in fresh._exit_checks.values():
        task.cancel()


# ── API ──────────────────────────────────────────────────────────────────────


async def test_endpoints_review_confirm_and_refuse_bad_tokens(world, monkeypatch):
    from backend.routers import trading as router
    from backend.trading import service

    monkeypatch.setattr(service, "broker", world.broker)
    req = router.PlanRequest(symbol="SOXL", direction="long", shares=100, entry=46.0, stop=44.5, target=49.0)
    review = await router.review(req)
    assert review["token"] and world.ib.placed == []
    bad = await router.confirm(router.ConfirmRequest(token="not-a-real-token"))
    assert bad.status_code == 409 and world.ib.placed == []
    placed = await router.confirm(router.ConfirmRequest(token=review["token"]))
    assert placed["state"] == "working" and len(world.ib.placed) == 3
    refused = await router.review(router.PlanRequest(symbol="SOXL", direction="long", shares=100, entry=46.0, stop=47.0, target=49.0))
    assert refused.status_code == 422 and "stop must be below" in json.loads(refused.body)["detail"]


async def test_state_lists_brackets_for_the_connected_account(world, monkeypatch):
    from backend.trading import service

    monkeypatch.setattr(service, "broker", world.broker)
    monkeypatch.setattr(service, "trading_session", world.session)
    await world.broker.confirm((await world.broker.review(LONG))["token"])
    state = await service.state()
    assert state["mode"] == "paper" and state["account"] == "DU123" and len(state["brackets"]) == 1
    assert state["settings"]["live_enabled"] in (True, False)


async def test_only_soxl_and_soxs_have_chart_bars():
    from backend.routers import trading as router

    with pytest.raises(router.HTTPException):
        await router.get_bars("TQQQ")


async def test_twss_directed_order_precaution_is_explained(world):
    world.now = NIGHT
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    entry = world.ib.trades()[0]
    world.broker._on_error(entry.order.orderId, 10329, "This order will be directly routed to OVERNIGHT.", None)
    await world.broker.apply_status(record["id"], "entry", status(entry, "Cancelled"))
    saved = await world.broker.bracket_record(record["id"])
    assert saved["state"] == "rejected" and "Bypass Redirect Order warning" in saved["warning"]


async def test_an_oca_cancellation_is_not_an_unprotected_warning(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    entry, stop, target = world.ib.trades()
    await world.broker.apply_status(record["id"], "entry", status(entry, "Filled"))
    world.broker._on_error(target.order.orderId, 202, "Order Canceled - reason:", None)
    await world.broker.apply_status(record["id"], "target", status(target, "Cancelled"))
    await world.broker.apply_status(record["id"], "stop", status(stop, "Filled"))
    saved = await world.broker.bracket_record(record["id"])
    assert saved["state"] == "closed" and saved["warning"] is None


async def test_reconcile_marks_exits_no_longer_open_at_ibkr_as_cancelled(world):
    record = await world.broker.confirm((await world.broker.review(LONG))["token"])
    entry, stop, target = world.ib.trades()

    async def open_orders():
        return [stop]

    world.ib.reqOpenOrdersAsync = open_orders
    await world.broker.apply_status(record["id"], "target", status(target, "PendingCancel"))
    await world.broker.reconcile(record["id"])
    orders = (await world.broker.bracket_record(record["id"]))["orders"]
    assert orders["target"]["status"] == "Cancelled" and orders["stop"]["status"] == "PreSubmitted"
