from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from backend.global_markets import service as gm
from backend.global_markets.instruments import INSTRUMENTS
from backend.global_markets.service import (
    GlobalMarketsService,
    Slot,
    due_daily,
    due_intraday,
    last_value,
    latest_session,
    previous_close,
    session_day,
)
from backend.macro.indicators import is_open, parse_trading_hours
from backend.routers import global_markets as router
from backend.services import ibkr_service

TOKYO = ZoneInfo("Asia/Tokyo")
# Tuesday Nov 3 has a lunch break; Wednesday is a holiday.
HOURS = "20261103:0900-20261103:1130;20261103:1230-20261103:1530;20261104:CLOSED;20261105:0900-20261105:1530"
MONDAY_OPEN = datetime(2026, 11, 3, 10, 0, tzinfo=TOKYO)


def hours():
    return parse_trading_hours(HOURS, "Japan")


def day_bar(d, close):
    return {"time": datetime(2026, 11, d, tzinfo=timezone.utc).timestamp(), "close": close}


def slot(**kwargs):
    return Slot(INSTRUMENTS[0], hours=hours(), **kwargs)


def test_five_cards_then_twelve_stocks():
    assert len({i.key for i in INSTRUMENTS}) == 17
    indexes = [i.key for i in INSTRUMENTS if i.section == "Indexes"]
    assert indexes == ["nikkei", "kospi200", "kodex200", "aex", "estx50"]
    assert len([i for i in INSTRUMENTS if i.section == "Chip stocks"]) == 12


def test_home_listings_not_us_ones():
    stocks = [i.make_contract() for i in INSTRUMENTS if i.section == "Chip stocks"]
    assert all(c.currency != "USD" and c.primaryExchange for c in stocks)


def test_lunch_break_and_holiday_are_closed():
    h = hours()
    assert is_open(h, MONDAY_OPEN)
    assert not is_open(h, datetime(2026, 11, 3, 12, 0, tzinfo=TOKYO))
    assert not is_open(h, datetime(2026, 11, 4, 10, 0, tzinfo=TOKYO))


def test_previous_close_is_before_the_session():
    daily = [day_bar(1, 90), day_bar(2, 100), day_bar(3, 105)]
    assert previous_close(daily, date(2026, 11, 3)) == 100
    assert previous_close(daily[:2], date(2026, 11, 3)) == 100


def test_previous_close_before_the_open_uses_the_last_two_sessions():
    assert previous_close([day_bar(1, 90), day_bar(2, 100)], None) == 90
    assert previous_close([day_bar(2, 100)], None) is None


def test_closed_market_uses_the_daily_close_from_the_auction():
    intraday, daily = [{"close": 1409.9}], [day_bar(2, 1412.8)]
    assert last_value(intraday, daily, False) == 1412.8
    assert last_value(intraday, daily, True) == 1409.9
    assert last_value(intraday, [], False) == 1409.9
    assert last_value([], [], False) is None


def test_only_the_latest_regular_session_is_kept():
    at = lambda d, h, m=0: {"time": datetime(2026, 10, d, h, m, tzinfo=TOKYO).timestamp()}  # noqa: E731
    friday = [at(30, 9), at(30, 15, 25), at(30, 17), at(30, 21)]
    assert latest_session(friday, "Asia/Tokyo", time(15, 30)) == friday[:2]
    monday = [*friday, {"time": datetime(2026, 11, 2, 9, 0, tzinfo=TOKYO).timestamp()}]
    assert latest_session(monday, "Asia/Tokyo", time(15, 30)) == monday[-1:]
    assert len(latest_session(friday, "Asia/Tokyo", None)) == 4


def test_amsterdam_stocks_name_their_exchange_for_the_closing_auction():
    contracts = {i.key: i.make_contract() for i in INSTRUMENTS}
    assert contracts["asml"].exchange == "AEB" and contracts["infineon"].exchange == "SMART"


def test_session_day_skips_a_holiday():
    assert session_day(hours(), datetime(2026, 11, 4, 10, 0, tzinfo=TOKYO)) == date(2026, 11, 3)
    assert session_day(hours(), datetime(2026, 11, 2, 10, 0, tzinfo=TOKYO)) is None


def test_open_market_refreshes_every_five_minutes():
    s = slot(tried_at=MONDAY_OPEN - timedelta(minutes=4))
    assert not due_intraday(s, MONDAY_OPEN)
    s.tried_at = MONDAY_OPEN - timedelta(minutes=5)
    assert due_intraday(s, MONDAY_OPEN)


def test_closed_market_stops_once_final_data_is_in():
    close = datetime(2026, 11, 3, 15, 30, tzinfo=TOKYO)
    now = close + timedelta(hours=2)
    assert due_intraday(slot(intraday_at=close + timedelta(minutes=10)), now)
    assert not due_intraday(slot(intraday_at=close + timedelta(minutes=31)), now)
    assert due_intraday(slot(), now)


def test_daily_refreshes_for_a_new_session():
    s = slot(daily_at=MONDAY_OPEN, daily_session=date(2026, 11, 3))
    assert not due_daily(s, MONDAY_OPEN + timedelta(minutes=10))
    assert due_daily(s, datetime(2026, 11, 5, 9, 5, tzinfo=TOKYO))


# ── Service ──────────────────────────────────────────────────────────────────


@pytest.fixture
def world(monkeypatch):
    state = SimpleNamespace(connected=True, requests=[], refuse=set(), empty=False, market_lines=0)

    async def details(contract):
        if contract.symbol in state.refuse:
            return []
        c = SimpleNamespace(conId=hash(contract.symbol), symbol=contract.symbol)
        return [SimpleNamespace(contract=c, liquidHours=HOURS, tradingHours="", timeZoneId="Japan")]

    async def bars(contract, duration, size, what, rth):
        state.requests.append((contract.symbol, size))
        if state.empty:
            return []
        if size == "1 day":
            return [day_bar(2, 100), day_bar(3, 102)]
        return [{"time": MONDAY_OPEN.timestamp() - 300, "close": 101.0}, {"time": MONDAY_OPEN.timestamp(), "close": 103.0}]

    monkeypatch.setattr(ibkr_service, "get_status", lambda: {"connected": state.connected})
    monkeypatch.setattr(ibkr_service, "get_historical_bars", bars)
    monkeypatch.setattr(ibkr_service.ibkr, "reqContractDetailsAsync", details)
    state.service = GlobalMarketsService(INSTRUMENTS[:2])
    return state


def card(world, key, monkeypatch, at=MONDAY_OPEN):
    monkeypatch.setattr(gm, "datetime", type("D", (datetime,), {"now": classmethod(lambda c, tz=None: at)}))
    return next(c for c in world.service.state()["instruments"] if c["key"] == key)


async def test_a_refresh_fills_the_card(world, monkeypatch):
    await world.service.tick(MONDAY_OPEN)
    c = card(world, "nikkei", monkeypatch)
    assert c["value"] == 103.0 and c["previous_close"] == 100 and c["change_pct"] == pytest.approx(3.0)
    assert c["market_open"] is True and len(c["sparkline"]) == 2 and c["error"] is None


async def test_delay_is_measured_from_the_end_of_the_latest_bar(world, monkeypatch):
    await world.service.tick(MONDAY_OPEN)
    later = MONDAY_OPEN + timedelta(minutes=22)
    assert card(world, "nikkei", monkeypatch, later)["delay_minutes"] == 17
    assert card(world, "nikkei", monkeypatch, MONDAY_OPEN + timedelta(minutes=2))["delay_minutes"] == 0


async def test_a_closed_market_shows_no_delay(world, monkeypatch):
    await world.service.tick(MONDAY_OPEN)
    assert card(world, "nikkei", monkeypatch, datetime(2026, 11, 3, 18, 0, tzinfo=TOKYO))["delay_minutes"] is None


async def test_the_etf_card_is_in_won_and_the_index_in_points(monkeypatch):
    monkeypatch.setattr(ibkr_service, "get_status", lambda: {"connected": True})
    cards = {c["key"]: c for c in GlobalMarketsService().state()["instruments"]}
    assert cards["kodex200"]["unit"] == "KRW" and cards["kospi200"]["unit"] == "pts"


async def test_a_refused_instrument_leaves_the_others_updating(world, monkeypatch):
    world.refuse.add("N225")
    await world.service.tick(MONDAY_OPEN)
    assert card(world, "nikkei", monkeypatch)["error"] == "IBKR has no contract for this"
    assert card(world, "kospi200", monkeypatch)["value"] == 103.0


async def test_an_ibkr_error_shows_on_its_card(world, monkeypatch):
    await world.service.tick(MONDAY_OPEN)
    contract = world.service.slots[0].contract
    world.service._on_error(1, 162, "Historical Market Data Service error message:No market data permissions", contract)
    assert card(world, "nikkei", monkeypatch)["error"] == "IBKR error 162: No market data permissions"
    assert card(world, "kospi200", monkeypatch)["error"] is None


async def test_an_empty_reply_keeps_the_values(world, monkeypatch):
    await world.service.tick(MONDAY_OPEN)
    world.empty = True
    await world.service.tick(MONDAY_OPEN + timedelta(minutes=5))
    assert card(world, "nikkei", monkeypatch)["value"] == 103.0


async def test_closed_markets_are_not_requested_again(world):
    late = datetime(2026, 11, 3, 18, 0, tzinfo=TOKYO)
    await world.service.tick(late)
    count = len(world.requests)
    await world.service.tick(late + timedelta(hours=2))
    assert len(world.requests) == count


async def test_disconnected_keeps_values_marked_stale(world, monkeypatch):
    await world.service.tick(MONDAY_OPEN)
    world.connected = False
    count = len(world.requests)
    await world.service.tick(MONDAY_OPEN + timedelta(minutes=5))
    world.service._on_disconnected()
    c = card(world, "nikkei", monkeypatch)
    assert len(world.requests) == count and c["stale"] is True and c["value"] == 103.0


async def test_reconnecting_resolves_contracts_again(world):
    await world.service.tick(MONDAY_OPEN)
    world.service._on_disconnected()
    assert world.service.slots[0].resolved_at is None and world.service.slots[0].tried_at is None


async def test_endpoint_returns_every_instrument(world, monkeypatch):
    monkeypatch.setattr(router, "global_markets_service", GlobalMarketsService())
    assert len((await router.get_state())["instruments"]) == 17


def test_no_order_or_market_data_line_calls():
    source = open(gm.__file__).read()
    for call in ("placeOrder", "cancelOrder", "reqMktData", "reqMarketDataType"):
        assert call not in source
