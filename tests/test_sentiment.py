import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend.macro import service as macro
from backend.macro.sentiment import (
    COMPONENTS,
    SOURCES,
    band_for,
    build_sentiment,
    moving_average,
    percentile_rank,
    period_return,
    vs_average,
)

DAY = 86_400.0
SYMBOLS = [s for s, _, _ in SOURCES]


def daily(values):
    return {i * DAY: float(v) for i, v in enumerate(values)}


def rising(days=500, rate=1.001):
    return daily([100 * rate**i for i in range(days)])


def all_closes(**overrides):
    return {**{s: rising() for s in SYMBOLS}, **overrides}


def component(result, key):
    return next(c for c in result["components"] if c["key"] == key)


def test_moving_average_and_distance_from_it():
    assert moving_average([1.0, 2.0, 3.0, 4.0], 2) == [None, 1.5, 2.5, 3.5]
    assert vs_average([1.0, 3.0], 2)[1] == pytest.approx(0.5)


def test_period_return():
    assert period_return([100.0, 110.0, 121.0], 2) == [None, None, pytest.approx(0.21)]


def test_percentile_counts_the_latest_value():
    assert percentile_rank([1.0, 2.0, 3.0, 4.0]) == 100
    assert percentile_rank([4.0, 3.0, 2.0, 1.0]) == 25


@pytest.mark.parametrize(
    ("score", "band"),
    [(0, "Extreme Fear"), (24.4, "Extreme Fear"), (24.6, "Fear"), (44, "Fear"), (45, "Neutral"), (55, "Neutral"), (56, "Greed"), (75, "Greed"), (76, "Extreme Greed"), (100, "Extreme Greed")],
)
def test_bands(score, band):
    assert band_for(score) == band


def test_every_component_explains_itself():
    for item in build_sentiment({}, {})["components"]:
        assert item["detail"] and item["meaning"]


def test_a_vix_spike_scores_as_fear():
    vix = [20.0 + i * 0.001 for i in range(499)] + [80.0]
    result = build_sentiment(all_closes(VIX=daily(vix)), {})
    assert component(result, "volatility")["score"] < 1


def test_the_years_highest_momentum_scores_100():
    spx = [100.0] * 499 + [200.0]
    assert component(build_sentiment(all_closes(SPX=daily(spx)), {}), "momentum")["score"] == 100


def test_score_is_the_plain_average_of_components():
    result = build_sentiment(all_closes(), {})
    scores = [c["score"] for c in result["components"] if c["in_score"]]
    assert len(scores) == 4
    assert result["score"] == pytest.approx(sum(scores) / 4)
    assert result["band"] == band_for(result["score"])
    assert len(result["history"]) == 60
    assert result["as_of"] == datetime.fromtimestamp(499 * DAY, timezone.utc).date().isoformat()


def test_one_refused_symbol_costs_only_its_components():
    closes = all_closes()
    del closes["HYG"]
    result = build_sentiment(closes, {"HYG": "IBKR error 354: no data"})
    junk = component(result, "junk")
    assert junk["score"] is None and "IBKR error 354" in junk["error"]
    others = [c["score"] for c in result["components"] if c["in_score"] and c["key"] != "junk"]
    assert len(others) == 3
    assert result["score"] == pytest.approx(sum(others) / 3)


def test_three_scored_components_are_enough():
    closes = all_closes()
    del closes["HYG"]
    assert build_sentiment(closes, {})["score"] is not None


def test_breadth_is_shown_but_never_scored():
    plain = build_sentiment(all_closes(), {})
    rsp = daily([100 * 1.001**i for i in range(499)] + [50.0])
    moved = build_sentiment(all_closes(RSP=rsp), {})
    assert component(moved, "breadth")["in_score"] is False
    assert component(moved, "breadth")["score"] != component(plain, "breadth")["score"]
    assert moved["score"] == plain["score"] and moved["history"] == plain["history"]


def test_breadth_alone_cannot_make_up_the_minimum():
    closes = all_closes()
    del closes["HYG"], closes["TLT"]
    result = build_sentiment(closes, {})
    assert result["score"] is None
    assert component(result, "breadth")["score"] is None


def test_losing_breadth_leaves_the_score_alone():
    closes = all_closes()
    plain = build_sentiment(closes, {})
    del closes["RSP"]
    result = build_sentiment(closes, {"RSP": "refused"})
    assert result["score"] == plain["score"]
    assert "refused" in component(result, "breadth")["error"]


def test_two_components_give_no_score_but_keep_the_reasons():
    closes = all_closes()
    del closes["HYG"], closes["TLT"], closes["RSP"]
    result = build_sentiment(closes, {"RSP": "refused"})
    assert result["score"] is None and result["band"] is None and result["history"] == []
    assert "refused" in component(result, "breadth")["error"]


def test_too_little_history_is_reported():
    result = build_sentiment(all_closes(SPX=rising(days=200)), {})
    assert component(result, "momentum")["error"] == "Not enough history"
    assert result["score"] is not None


def test_empty_data_has_no_score():
    result = build_sentiment({}, {})
    assert result["score"] is None and result["as_of"] is None and len(result["components"]) == len(COMPONENTS)


class FakeIB:
    def __init__(self):
        self.connected = True

    def isConnected(self):
        return self.connected

    async def qualifyContractsAsync(self, *contracts):
        return list(contracts)


@pytest.fixture
def install(monkeypatch):
    ib = FakeIB()
    monkeypatch.setattr(macro.ibkr_service, "ibkr", ib)
    monkeypatch.setattr(macro.ibkr_service, "get_status", lambda: {"connected": ib.connected})

    def _install(bars_for):
        calls = []

        async def fake_bars(contract, duration, bar_size, what_to_show, use_rth):
            calls.append((contract.symbol, duration, bar_size, what_to_show, use_rth))
            return bars_for(contract.symbol)

        monkeypatch.setattr(macro.ibkr_service, "get_historical_bars", fake_bars)
        return calls

    return ib, _install


def bars():
    return [{"time": i * DAY, "close": 100.0 * 1.001**i} for i in range(500)]


NOW = datetime(2026, 11, 2, tzinfo=timezone.utc)


async def test_refresh_requests_daily_history_one_symbol_at_a_time(install):
    _, setup = install
    calls = setup(lambda s: bars())
    service = macro.MacroService(indicators=[])
    await service.refresh_sentiment(NOW)
    assert [c[0] for c in calls] == SYMBOLS
    assert all(c[1:3] == ("2 Y", "1 day") and c[4] is True for c in calls)
    assert dict((c[0], c[3]) for c in calls)["TLT"] == "ADJUSTED_LAST"
    assert dict((c[0], c[3]) for c in calls)["SPX"] == "TRADES"
    assert service.state()["sentiment"]["score"] is not None
    assert service.state()["sentiment"]["stale"] is False


async def test_a_refused_symbol_shows_ibkrs_error_and_the_rest_still_score(install):
    _, setup = install
    service = macro.MacroService(indicators=[])

    def bars_for(symbol):
        if symbol == "HYG":
            service._on_error(9, 162, "No market data permissions", SimpleNamespace(symbol="HYG", conId=1))
            return []
        return bars()

    setup(bars_for)
    await service.refresh_sentiment(NOW)
    junk = component(service.sentiment, "junk")
    assert junk["score"] is None and "No market data permissions" in junk["error"]
    assert service.sentiment["score"] is not None


async def test_recovery_clears_a_symbols_error(install):
    _, setup = install
    refused = {"HYG"}
    setup(lambda s: [] if s in refused else bars())
    service = macro.MacroService(indicators=[])
    await service.refresh_sentiment(NOW)
    assert component(service.sentiment, "junk")["error"]
    refused.clear()
    await service.refresh_sentiment(NOW)
    assert component(service.sentiment, "junk")["error"] is None


async def test_a_drop_during_refresh_keeps_the_last_score_and_retries_on_reconnect(install):
    ib, setup = install
    setup(lambda s: bars())
    service = macro.MacroService(indicators=[])
    await service.refresh_sentiment(NOW)
    before = service.sentiment

    def drop(symbol):
        ib.connected = False
        return []

    setup(drop)
    await service.refresh_sentiment(NOW)
    assert service.sentiment is before
    service._on_disconnected()
    assert service._sentiment_at is None
    assert service.state()["sentiment"]["stale"] is True


async def test_loop_waits_for_the_hour(install, monkeypatch):
    _, setup = install
    calls = setup(lambda s: bars())
    service = macro.MacroService(indicators=[])
    real_sleep = asyncio.sleep
    monkeypatch.setattr(macro.asyncio, "sleep", lambda _: real_sleep(0))
    task = asyncio.create_task(service._sentiment_loop())
    await real_sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(calls) == len(SYMBOLS)


def test_state_without_a_score_yet(install):
    service = macro.MacroService(indicators=[])
    assert service.state()["sentiment"] is None
