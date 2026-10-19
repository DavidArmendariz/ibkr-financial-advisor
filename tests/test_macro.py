from datetime import datetime, timedelta, timezone

import httpx
import pytest
from ib_async import ContFuture, Future

from backend.macro import service as macro
from backend.macro import trm
from backend.macro.indicators import INDICATORS, change_fields, freshness, is_open, parse_trading_hours
from backend.signals.sessions import ET

CL_HOURS = "20261017:CLOSED;20261018:1800-20261019:1700;20261019:1800-20261020:1700"


def test_price_change_and_percent():
    c = change_fields(72.40, 71.90, "pct")
    assert c["change"] == pytest.approx(0.50)
    assert round(c["change_pct"], 2) == 0.70
    assert c["change_bp"] is None


def test_yield_change_in_basis_points():
    c = change_fields(4.31, 4.25, "bp")
    assert round(c["change_bp"]) == 6
    assert c["change_pct"] is None


def test_missing_previous_close():
    assert change_fields(72.40, None, "pct") == {"change": None, "change_pct": None, "change_bp": None}


def test_overnight_futures_session():
    hours = parse_trading_hours(CL_HOURS, "US/Eastern")
    assert not is_open(hours, datetime(2026, 10, 17, 12, 0, tzinfo=ET))  # Saturday
    assert is_open(hours, datetime(2026, 10, 18, 22, 0, tzinfo=ET))  # Sunday evening
    assert is_open(hours, datetime(2026, 10, 19, 3, 0, tzinfo=ET))  # overnight
    assert not is_open(hours, datetime(2026, 10, 19, 17, 30, tzinfo=ET))  # daily break


def test_trading_hours_in_exchange_time_zone():
    hours = parse_trading_hours("20261019:0720-20261019:1400", "US/Central")
    assert is_open(hours, datetime(2026, 10, 19, 14, 30, tzinfo=ET))  # 13:30 CT
    assert not is_open(hours, datetime(2026, 10, 19, 15, 30, tzinfo=ET))  # 14:30 CT


def test_vix_two_sessions_a_day():
    for hours in (
        "20261019:0215-20261019:0815;20261019:0830-20261019:1600",
        "20261019:0215-20261019:0815,20261019:0830-20261019:1600",
    ):
        parsed = parse_trading_hours(hours, "US/Central")
        assert is_open(parsed, datetime(2026, 10, 19, 4, 0, tzinfo=ET))  # 03:00 CT
        assert not is_open(parsed, datetime(2026, 10, 19, 9, 20, tzinfo=ET))  # gap between sessions
        assert is_open(parsed, datetime(2026, 10, 19, 12, 0, tzinfo=ET))


def test_indicator_order():
    assert [i.key for i in INDICATORS] == [
        "crude", "gold", "es", "nq", "dow", "us10y", "vix", "usdcop", "spx", "ndx", "dji",
    ]


def test_freshness_labels():
    assert freshness(False, 1, True) == "closed"
    assert freshness(True, 1, True) == "live"
    assert freshness(True, 3, True) == "delayed"
    assert freshness(True, 1, False) == "delayed"


# ── Service ─────────────────────────────────────────────────────────────────

CRUDE = INDICATORS[0]
NOW = datetime.now(timezone.utc)
OPEN_HOURS = [(NOW - timedelta(hours=1), NOW + timedelta(hours=1))]


class FakeTicker:
    def __init__(self, contract, price=float("nan"), close=float("nan"), mdt=1):
        self.contract, self.price, self.close, self.marketDataType = contract, price, close, mdt
        self.time = NOW

    def marketPrice(self):
        return self.price


class FakeDetails:
    tradingHours = ""
    timeZoneId = "US/Eastern"
    contractMonth = "202612"


class FakeIB:
    def __init__(self):
        self.front = 1001
        self.calls = []

    def isConnected(self):
        return True

    async def qualifyContractsAsync(self, contract):
        if isinstance(contract, ContFuture):
            return [ContFuture(conId=self.front, symbol="CL", exchange="NYMEX")]
        contract.localSymbol = {1001: "CLZ6", 1002: "CLF7"}[contract.conId]
        return [contract]

    async def reqContractDetailsAsync(self, contract):
        return [FakeDetails()]

    def reqMarketDataType(self, t):
        self.calls.append(("type", t))

    def reqMktData(self, contract, *args):
        self.calls.append(("sub", contract.conId))
        return FakeTicker(contract)

    def cancelMktData(self, contract):
        self.calls.append(("cancel", contract.conId))


@pytest.fixture
def svc(monkeypatch):
    ib = FakeIB()
    monkeypatch.setattr(macro.ibkr_service, "ibkr", ib)
    monkeypatch.setattr(macro.ibkr_service, "get_status", lambda: {"connected": True})

    async def no_bars(*args, **kwargs):
        return []

    monkeypatch.setattr(macro.ibkr_service, "get_historical_bars", no_bars)
    return macro.MacroService([CRUDE]), ib


async def test_subscribes_to_front_month_with_delayed_fallback(svc):
    service, ib = svc
    await service._tick()
    assert ib.calls == [("type", 4), ("sub", 1001)]
    assert isinstance(service.slots[0].contract, Future)
    assert service.state()["indicators"][0]["contract"] == "CLZ6"


async def test_rollover_resubscribes_to_new_month(svc):
    service, ib = svc
    await service._tick()
    ib.front = 1002
    service.slots[0].resolved_at -= macro.RESOLVE_INTERVAL
    await service._tick()
    assert ib.calls[-3:] == [("cancel", 1001), ("type", 4), ("sub", 1002)]
    assert service.state()["indicators"][0]["contract"] == "CLF7"


async def test_same_month_keeps_subscription(svc):
    service, ib = svc
    await service._tick()
    service.slots[0].resolved_at -= macro.RESOLVE_INTERVAL
    await service._tick()
    assert ib.calls == [("type", 4), ("sub", 1001)]


async def test_refused_data_shows_error_and_retries_later(svc):
    service, ib = svc
    await service._tick()
    service._on_error(5, 354, "Requested market data is not subscribed.", service.slots[0].contract)
    state = service.state()["indicators"][0]
    assert state["error"] == "IBKR error 354: Requested market data is not subscribed."
    assert ib.calls[-1] == ("cancel", 1001)
    await service._tick()
    assert ib.calls[-1] == ("cancel", 1001)  # waits RETRY_INTERVAL before resubscribing


DENIED = "Historical Market Data Service error message:No market data permissions for CME IND"


@pytest.fixture
def bar_requests(svc, monkeypatch):
    service, _ = svc
    requests = []

    # IBKR's error arrives while the request is still pending.
    async def record(contract, *args, **kwargs):
        requests.append(contract.conId)
        if service.deny_history:
            service._on_error(7, 162, DENIED, contract)
        return []

    service.deny_history = False
    monkeypatch.setattr(macro.ibkr_service, "get_historical_bars", record)
    return requests


def _bars_due(service):
    service.slots[0].bars_at -= macro.BARS_INTERVAL


async def test_history_without_permission_is_not_requested_again(svc, bar_requests):
    service, ib = svc
    service.deny_history = True
    await service._tick()
    assert len(bar_requests) == 1  # the daily request isn't sent after the denial
    _bars_due(service)
    await service._tick()
    assert len(bar_requests) == 1
    assert service.state()["indicators"][0]["error"] == "IBKR error 162: No market data permissions for CME IND"


async def test_other_history_errors_keep_retrying(svc, bar_requests):
    service, ib = svc
    await service._tick()
    service._on_error(7, 162, "Historical Market Data Service error message:HMDS query returned no data", service.slots[0].contract)
    _bars_due(service)
    await service._tick()
    assert len(bar_requests) == 4


async def test_history_permission_rechecked_after_reconnect(svc, bar_requests):
    service, ib = svc
    await service._tick()
    service._on_error(7, 162, DENIED, service.slots[0].contract)
    service._on_disconnected()
    _bars_due(service)
    await service._tick()
    assert len(bar_requests) == 4


def _slot(**kwargs):
    slot = macro.Slot(CRUDE, contract=Future(conId=1001, localSymbol="CLZ6"), **kwargs)
    return macro.MacroService([CRUDE]), slot


@pytest.mark.parametrize(
    "hours, mdt, expected",
    [(OPEN_HOURS, 1, "live"), (OPEN_HOURS, 3, "delayed"), ([], 1, "closed")],
)
def test_streamed_value_labelling(svc, hours, mdt, expected):
    service, slot = _slot(hours=hours)
    slot.ticker = FakeTicker(slot.contract, price=72.40, close=71.90, mdt=mdt)
    s = service._indicator_state(slot, NOW, connected=True)
    assert s["freshness"] == expected
    assert s["value"] == 72.40 and s["previous_close"] == 71.90
    assert round(s["change_pct"], 2) == 0.70


def test_closed_market_falls_back_to_daily_bars(svc):
    # Delayed data streams nothing once the market is closed.
    service, slot = _slot(daily=[96.50, 99.02])
    slot.ticker = FakeTicker(slot.contract)
    s = service._indicator_state(slot, NOW, connected=True)
    assert (s["value"], s["previous_close"], s["freshness"]) == (99.02, 96.50, "closed")


def test_closed_market_ignores_stream_rolled_to_next_session(svc):
    # VIX overnight: IBKR streams Friday's close as both last and close.
    service, slot = _slot(daily=[16.46, 19.99])
    slot.ticker = FakeTicker(slot.contract, price=19.99, close=19.99, mdt=3)
    s = service._indicator_state(slot, NOW, connected=True)
    assert (s["value"], s["previous_close"], s["freshness"]) == (19.99, 16.46, "closed")


def test_disconnect_keeps_last_value_marked_stale(svc):
    service, slot = _slot(hours=OPEN_HOURS, daily=[96.50, 99.02])
    slot.ticker = FakeTicker(slot.contract, price=99.50, close=99.02)
    service._indicator_state(slot, NOW, connected=True)
    service.slots = [slot]
    service._on_disconnected()
    s = service._indicator_state(slot, NOW, connected=False)
    assert (s["value"], s["stale"]) == (99.50, True)


def test_refused_history_shows_when_card_has_no_value(svc):
    service, slot = _slot()
    service.slots = [slot]
    service._on_error(7, 162, "Historical Market Data Service error message:No market data permissions for CME IND", slot.contract)
    assert service._indicator_state(slot, NOW, connected=True)["error"] == "IBKR error 162: No market data permissions for CME IND"
    slot.daily = [96.50, 99.02]
    assert service._indicator_state(slot, NOW, connected=True)["error"] is None


def test_yield_is_scaled_to_percent(svc):
    tnx = next(i for i in INDICATORS if i.key == "us10y")
    service = macro.MacroService([tnx])
    slot = macro.Slot(tnx, daily=[50.89, 50.98])
    s = service._indicator_state(slot, NOW, connected=True)
    assert s["value"] == pytest.approx(5.098)
    assert round(s["change_bp"]) == 1


# ── USD/COP (TRM) ───────────────────────────────────────────────────────────

TRM_ROWS = [
    {"valor": "3174.67", "vigenciadesde": "2026-10-17T00:00:00.000", "vigenciahasta": "2026-10-19T00:00:00.000"},
    {"valor": "3170.46", "vigenciadesde": "2026-10-16T00:00:00.000", "vigenciahasta": "2026-10-16T00:00:00.000"},
    {"valor": "3197.65", "vigenciadesde": "2026-10-15T00:00:00.000", "vigenciahasta": "2026-10-15T00:00:00.000"},
]
USDCOP = next(i for i in INDICATORS if i.key == "usdcop")
SUNDAY_BOGOTA = datetime(2026, 10, 18, 12, 0, tzinfo=trm.BOGOTA)


def test_trm_weekend_rate_and_change():
    feed = trm.TrmFeed(USDCOP)
    feed.rates = trm.parse_rows(TRM_ROWS)
    s = feed.state(SUNDAY_BOGOTA)
    assert (s["value"], s["previous_close"]) == (3174.67, 3170.46)
    assert (s["valid_from"], s["valid_to"]) == ("2026-10-17", "2026-10-19")
    assert round(s["change_pct"], 2) == 0.13
    assert s["freshness"] == "daily" and s["stale"] is False
    assert [p["value"] for p in s["sparkline"]] == [3197.65, 3170.46, 3174.67]


def test_trm_published_for_tomorrow_is_not_shown_yet():
    rows = [{"valor": "3200.00", "vigenciadesde": "2026-10-20T00:00:00.000", "vigenciahasta": "2026-10-20T00:00:00.000"}]
    feed = trm.TrmFeed(USDCOP)
    feed.rates = trm.parse_rows(rows + TRM_ROWS)
    s = feed.state(SUNDAY_BOGOTA)
    assert s["value"] == 3174.67
    assert 3200.00 not in [p["value"] for p in s["sparkline"]]


async def test_trm_fetch_and_failure_keeps_last_rate():
    feed = trm.TrmFeed(USDCOP)
    ok = httpx.MockTransport(lambda req: httpx.Response(200, json=TRM_ROWS))
    assert await feed.fetch(ok)
    down = httpx.MockTransport(lambda req: httpx.Response(503))
    assert not await feed.fetch(down)
    s = feed.state(SUNDAY_BOGOTA)
    assert s["value"] == 3174.67
    assert s["error"].startswith("Couldn't load the TRM")


def test_trm_card_keeps_its_place_in_the_list(svc):
    service = macro.MacroService(INDICATORS)
    service.trm.rates = trm.parse_rows(TRM_ROWS)
    keys = [i["key"] for i in service.state()["indicators"]]
    assert keys == [i.key for i in INDICATORS]
