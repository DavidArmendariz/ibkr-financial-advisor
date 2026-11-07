from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.planner import calc, config as planner_config, service as planner_module
from backend.planner.service import PlannerService
from backend.routers import planner as planner_router
from backend.services import ibkr_service
from backend.signals.sessions import ET

NOW = datetime(2026, 11, 5, 11, 0, tzinfo=ET)


def test_the_spec_example():
    p = calc.plan(80.0, 0.40, 1.5, 3, 1000, None)
    assert (p["stop"], p["target"], p["shares"]) == (79.4, 81.2, 1666)
    assert p["risk_dollars"] == pytest.approx(999.6) and p["reward_risk"] == pytest.approx(2.0)
    assert p["stop_pct"] == pytest.approx(-0.75) and p["exceeds_funds"] is False


def test_shares_round_down_and_exact_divisions_hold():
    assert calc.plan(10.0, 0.5, 1, 2, 1000, None)["shares"] == 2000
    assert calc.plan(10.0, 0.3, 1, 2, 100, None)["shares"] == 333


def test_risk_from_net_liquidation():
    assert calc.risk_amount("percent", 1, 500, 100_000) == 1000
    assert calc.risk_amount("dollars", 1, 500, 100_000) == 500
    assert calc.risk_amount("percent", 1, 500, None) is None


def test_warns_above_available_funds():
    assert calc.plan(80.0, 0.40, 1.5, 3, 1000, 50_000)["exceeds_funds"] is True
    assert calc.plan(80.0, 0.40, 1.5, 3, 1000, 500_000)["exceeds_funds"] is False


@pytest.mark.parametrize(
    "args,fragment",
    [
        ((80.0, None, 1.5, 3, 1000, None), "No ATR"),
        ((80.0, 0.4, 1.5, 3, None, None), "net liquidation"),
        ((0, 0.4, 1.5, 3, 1000, None), "above zero"),
        ((80.0, 0.4, -1, 3, 1000, None), "above zero"),
        ((1.0, 0.8, 2, 3, 1000, None), "below zero"),
        ((80.0, 0.4, 1.5, 3, 0.1, None), "one share"),
    ],
)
def test_invalid_inputs_explain_why(args, fragment):
    p = calc.plan(*args)
    assert p["ok"] is False and fragment in p["reason"]


def bar(minute, high, low, close, day=4):
    return {"time": datetime(2026, 11, day, 14, minute, tzinfo=timezone.utc).timestamp(), "open": close, "high": high, "low": low, "close": close, "volume": 1}


def test_atr_from_bars_and_aggregation():
    bars = [bar(i, 11, 9, 10) for i in range(4)]
    assert calc.atr_from_bars(bars, 3) == pytest.approx(2.0)
    five = calc.aggregate([bar(i, 10 + i, 9, 10 + i) for i in range(10)], 5)
    assert len(five) == 2 and (five[0]["high"], five[0]["low"], five[0]["close"]) == (14, 9, 14)


def test_todays_partial_daily_bar_is_dropped_until_the_close():
    days = [{"time": datetime(2026, 11, d, tzinfo=timezone.utc).timestamp()} for d in (3, 4, 5)]
    assert len(calc.completed_days(days, NOW)) == 2
    assert len(calc.completed_days(days, NOW.replace(hour=16, minute=30))) == 3


def test_settings_validate_before_saving(monkeypatch):
    saved = {}
    monkeypatch.setattr(planner_config, "save_env_values", saved.update)
    planner_config.get_planner_settings.cache_clear()
    monkeypatch.delenv("PLANNER_STOP_MULTIPLE", raising=False)
    with pytest.raises(Exception):
        planner_config.save_planner_settings({"stop_multiple": -1})
    assert saved == {}
    planner_config.save_planner_settings({"stop_multiple": 2.0})
    assert saved == {"PLANNER_STOP_MULTIPLE": "2.0"}
    planner_config.get_planner_settings.cache_clear()


# ── Service ──────────────────────────────────────────────────────────────────


@pytest.fixture
def world(monkeypatch):
    state = SimpleNamespace(requests=[], refuse=set())

    async def bars(contract, duration, size, what, rth):
        state.requests.append((contract.symbol, size))
        if contract.symbol in state.refuse:
            return []
        if size == "1 day":
            return [{"time": datetime(2026, 10, d, tzinfo=timezone.utc).timestamp(), "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1} for d in range(1, 21)]
        return [bar(i % 60, 10.2, 9.8, 10.0) for i in range(30)]

    monkeypatch.setattr(ibkr_service.ibkr, "isConnected", lambda: True)
    monkeypatch.setattr(ibkr_service, "get_historical_bars", bars)
    monkeypatch.setattr(planner_module.signal_service, "pipeline", None)
    state.subscribed, state.cancelled, state.types = [], [], []

    async def qualify(*contracts):
        for c in contracts:
            c.conId = hash(c.symbol) % 1000 + 1
        return list(contracts)

    def req_mkt_data(contract, *args):
        if not contract.conId:
            raise ValueError("unqualified contract")
        state.subscribed.append(contract.symbol)
        return SimpleNamespace(contract=contract, bid=state.bid, ask=state.ask, time=NOW, marketDataType=1)

    state.bid, state.ask = 9.98, 10.02
    monkeypatch.setattr(ibkr_service.ibkr, "qualifyContractsAsync", qualify)
    monkeypatch.setattr(ibkr_service.ibkr, "reqMktData", req_mkt_data)
    monkeypatch.setattr(ibkr_service.ibkr, "cancelMktData", lambda contract: state.cancelled.append(contract.symbol))
    monkeypatch.setattr(ibkr_service.ibkr, "reqMarketDataType", state.types.append)
    state.service = PlannerService()
    return state


async def test_both_symbols_get_price_and_atr(world):
    await world.service.refresh(NOW)
    soxs = world.service.quote_state("SOXS")
    assert soxs["price"] == 10.0 and soxs["intraday_atr"] == pytest.approx(0.4) and soxs["daily_atr"] == pytest.approx(2.0)
    assert soxs["intraday_pct"] == pytest.approx(4.0) and soxs["error"] is None


async def test_bars_are_cached_between_refreshes(world):
    await world.service.refresh(NOW)
    count = len(world.requests)
    await world.service.refresh(NOW + timedelta(seconds=30))
    assert len(world.requests) == count
    await world.service.refresh(NOW + timedelta(seconds=61))
    assert len(world.requests) == count + 2


async def test_a_refused_symbol_leaves_the_other_working(world):
    world.refuse.add("SOXS")
    await world.service.refresh(NOW)
    assert world.service.quote_state("SOXS")["error"] and world.service.quote_state("SOXL")["price"] == 10.0


async def test_an_ibkr_error_shows_on_its_symbol(world):
    world.service._on_error(1, 162, "Historical Market Data Service error message:No market data permissions", SimpleNamespace(symbol="SOXS"))
    assert world.service.quote_state("SOXS")["error"] == "IBKR error 162: No market data permissions"
    assert world.service.quote_state("SOXL")["error"] is None


async def test_live_soxl_comes_from_the_signal_pipeline(world, monkeypatch):
    pipeline = SimpleNamespace(last_bar=SimpleNamespace(time=NOW, close=80.0), last_values=SimpleNamespace(atr=0.4))
    monkeypatch.setattr(planner_module.signal_service, "pipeline", pipeline)
    monkeypatch.setattr(planner_module.signal_service, "last_price", 80.5)
    await world.service.refresh(NOW)
    soxl = world.service.quote_state("SOXL")
    assert soxl["price"] == 80.5 and soxl["intraday_atr"] == 0.4
    assert ("SOXL", "1 min") not in world.requests


async def test_plan_endpoint_uses_the_quote_and_account(world, monkeypatch):
    async def summary():
        return {"NetLiquidation": 100_000.0, "AvailableFunds": 50_000.0}

    monkeypatch.setattr(ibkr_service, "get_account_summary", summary)
    monkeypatch.setattr(planner_router, "planner_service", world.service)
    await world.service.refresh(NOW)
    req = planner_router.PlanRequest(symbol="SOXS", atr_basis="intraday", stop_multiple=1.5, target_multiple=3, risk_mode="percent", risk_percent=1, risk_dollars=500)
    p = await planner_router.make_plan(req)
    assert p["ok"] and p["entry"] == 10.02 and p["stop"] == 9.42 and p["shares"] == 1666 and p["exceeds_funds"] is False


async def test_quotes_stream_while_wanted_and_drop_when_idle(world):
    await world.service.refresh(NOW)
    await world.service.refresh(NOW + timedelta(seconds=30))
    assert world.subscribed == ["SOXL", "SOXS"] and world.types == [1]
    soxs = world.service.quote_state("SOXS")
    assert (soxs["bid"], soxs["ask"], soxs["quote_delayed"]) == (9.98, 10.02, False)
    world.service.drop_if_idle(NOW + timedelta(seconds=90))
    assert world.cancelled == []
    world.service.drop_if_idle(NOW + timedelta(seconds=151))
    assert world.cancelled == ["SOXL", "SOXS"] and world.service.quote_state("SOXS")["ask"] is None


async def test_a_crossed_or_missing_quote_falls_back_to_the_last_price(world, monkeypatch):
    world.bid, world.ask = 10.5, 10.4
    await world.service.refresh(NOW)
    assert world.service.quote_state("SOXS")["ask"] is None

    async def summary():
        return {"NetLiquidation": 100_000.0}

    monkeypatch.setattr(ibkr_service, "get_account_summary", summary)
    monkeypatch.setattr(planner_router, "planner_service", world.service)
    req = planner_router.PlanRequest(symbol="SOXS", atr_basis="intraday", stop_multiple=1.5, target_multiple=3, risk_mode="dollars", risk_percent=1, risk_dollars=1000)
    assert (await planner_router.make_plan(req))["entry"] == 10.0


async def test_reconnecting_subscribes_again(world):
    await world.service.refresh(NOW)
    world.service._on_disconnected()
    await world.service.refresh(NOW + timedelta(seconds=5))
    assert world.subscribed == ["SOXL", "SOXS", "SOXL", "SOXS"]
