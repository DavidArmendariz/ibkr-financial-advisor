import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from backend import database
from backend.fundamentals import analysis, calc, news
from backend.fundamentals import service as fs
from backend.fundamentals.finnhub import Finnhub, FinnhubError, RateLimited
from backend.fundamentals.service import FundamentalsError, FundamentalsService
from backend.routers import fundamentals as router
from backend.services import ibkr_service

NOW = datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc)


# ── Calculations ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw,expected", [("nvda", "NVDA"), (" BRK.B ", "BRK.B"), ("RDS-A", "RDS-A"), ("", None), ("A B", None), ("TOOLONGTICKER", None), ("../x", None)])
def test_ticker_check(raw, expected):
    assert calc.clean_ticker(raw) == expected


def test_peers_drop_the_stock_itself_and_repeats():
    peers = ["NVDA", "AVGO", "MU", "AMD", "MRVL", "MRVL", "avgo"] + [f"P{i}" for i in range(10)]
    cleaned = calc.clean_peers("NVDA", peers)
    assert cleaned[:4] == ["AVGO", "MU", "AMD", "MRVL"] and "NVDA" not in cleaned
    assert len(cleaned) == calc.MAX_PEERS and len(set(cleaned)) == len(cleaned)


def test_peer_median_needs_three_positive_values():
    assert calc.peer_median([10, 20, 400]) == 20  # a median isn't skewed by one outlier
    assert calc.peer_median([10, 20, None, -5]) is None
    assert calc.peer_median([10, 20, 30, -5, None]) == 20


def test_history_median_uses_the_last_five_fiscal_years():
    series = [{"period": f"{2026 - i}-01-31", "v": v} for i, v in enumerate([30, 20, 25, 40, 35, 1, 1])]
    assert calc.history_median(series) == (30, 5)
    short = [{"period": "2026-01-31", "v": 10}, {"period": "2025-01-31", "v": -3}, {"period": "2024-01-31", "v": 12}]
    assert calc.history_median(short) == (None, 2)


def test_cheaper_at_twenty_percent_below():
    assert calc.cheaper(12, 20) is True
    assert calc.cheaper(16, 20) is True  # exactly 20% below
    assert calc.cheaper(16.1, 20) is False
    assert calc.cheaper(12, None) is None
    assert calc.cheaper(-5, 20) is None


def test_compare_marks_peers_history_and_losses():
    metric = {"peTTM": 18.0, "evEbitdaTTM": 12.0, "psTTM": -1.0, "pbQuarterly": 3.0}
    series = {"pe": [{"period": f"{2026 - i}-01-31", "v": 25} for i in range(5)], "evEbitda": []}
    peers = [{"evEbitdaTTM": v, "peTTM": 30} for v in (18, 20, 22)]
    rows = {r["key"]: r for r in calc.compare(metric, series, peers)}
    assert rows["pe"]["cheaper_than_history"] is True and rows["pe"]["history_median"] == 25
    assert rows["ev_ebitda"]["cheaper_than_peers"] is True and rows["ev_ebitda"]["peer_median"] == 20
    assert rows["ev_ebitda"]["history_median"] is None and rows["ev_ebitda"]["history_years"] == 0
    assert rows["ps"]["status"] == "not_meaningful" and rows["ps"]["value"] is None
    assert rows["ev_fcf"]["status"] == "missing" and rows["ev_fcf"]["has_history"] is False
    assert rows["pb"]["peer_median"] is None and rows["pb"]["peer_count"] == 0


def test_loss_making_pe_is_not_meaningful():
    row = calc.compare({"peTTM": -12.5}, {}, [])[0]
    assert row["key"] == "pe" and row["status"] == "not_meaningful" and row["cheaper_than_peers"] is None
    # Finnhub's shape for a loss-maker such as RIVN: no P/E at all, negative EPS.
    rivn = calc.compare({"peTTM": None, "epsTTM": -2.252}, {}, [])[0]
    assert rivn["status"] == "not_meaningful" and rivn["value"] is None
    assert calc.compare({"epsTTM": 1.5}, {}, [])[0]["status"] == "missing"


def test_ratings_latest_and_previous_month():
    rows = [
        {"period": "2026-10-01", "strongBuy": 24, "buy": 38, "hold": 4, "sell": 1, "strongSell": 0},
        {"period": "2026-11-01", "strongBuy": 25, "buy": 41, "hold": 2, "sell": 1, "strongSell": 0},
    ]
    r = calc.ratings(rows)
    assert r["latest"]["period"] == "2026-11-01" and r["latest"]["total"] == 69
    assert r["latest"]["buy_share"] == pytest.approx(66 / 69) and r["previous"]["buy"] == 38
    assert calc.ratings([]) is None


# ── Finnhub client ───────────────────────────────────────────────────────────

PROFILES = {"NVDA": {"name": "NVIDIA Corporation", "finnhubIndustry": "Semiconductors", "exchange": "NASDAQ", "currency": "USD", "marketCapitalization": 4498024.1}}
METRICS = {
    "NVDA": {"peTTM": 22.69, "psTTM": 14.45, "evEbitdaTTM": 21.81, "currentEv/freeCashFlowTTM": 34.5, "pbQuarterly": 20.8, "revenueGrowthTTMYoy": 83.4, "roeTTM": 110.1},
    "AVGO": {"peTTM": 60.0, "psTTM": 20.0, "evEbitdaTTM": 35.0},
    "MU": {"peTTM": 15.0, "psTTM": 5.0, "evEbitdaTTM": 8.0},
    "AMD": {"peTTM": 90.0, "psTTM": 9.0, "evEbitdaTTM": 45.0},
}
SERIES = {"pe": [{"period": f"{2026 - i}-01-25", "v": v} for i, v in enumerate([37.7, 39.8, 51.8, 45.0, 60.0])]}


@pytest.fixture
def finnhub(monkeypatch):
    state = SimpleNamespace(calls=[], status={}, keys=set())

    def handler(request: httpx.Request) -> httpx.Response:
        endpoint = request.url.path.removeprefix("/api/v1/")
        symbol = request.url.params.get("symbol")
        state.calls.append((endpoint, symbol))
        state.keys.add(request.headers.get("X-Finnhub-Token"))
        assert "token" not in request.url.params
        if endpoint in state.status:
            return httpx.Response(state.status[endpoint])
        if endpoint == "stock/profile2":
            return httpx.Response(200, json=PROFILES.get(symbol, {}))
        if endpoint == "stock/metric":
            return httpx.Response(200, json={"metric": METRICS.get(symbol, {}), "series": {"annual": SERIES if symbol == "NVDA" else {}}})
        if endpoint == "quote":
            return httpx.Response(200, json={"c": 182.5, "dp": -1.2})
        if endpoint == "stock/peers":
            return httpx.Response(200, json=["NVDA", "AVGO", "MU", "AMD", "AMD"])
        if endpoint == "stock/recommendation":
            return httpx.Response(200, json=[{"period": "2026-11-01", "strongBuy": 25, "buy": 41, "hold": 2, "sell": 1, "strongSell": 0}])
        if endpoint == "company-news":
            return httpx.Response(200, json=[
                {"datetime": NOW.timestamp() - 600, "headline": "Nvidia unveils new chip", "source": "Reuters", "url": "https://example.com/a"},
                {"datetime": NOW.timestamp() - 7200, "headline": "Older story", "source": "Yahoo", "url": "javascript:alert(1)"},
                {"headline": "no time"},
            ])
        return httpx.Response(404)

    state.client = Finnhub("secret-key-1234", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return state


async def test_client_parses_probe_shaped_replies(finnhub):
    fh = finnhub.client
    assert (await fh.profile("NVDA"))["finnhubIndustry"] == "Semiconductors"
    metric, series = await fh.metrics("NVDA")
    assert metric["peTTM"] == 22.69 and len(series["pe"]) == 5
    items = await fh.news("NVDA", date(2026, 11, 7))
    assert [i["headline"] for i in items] == ["Nvidia unveils new chip", "Older story"]
    assert items[1]["url"] is None  # only https links are kept
    assert finnhub.keys == {"secret-key-1234"}


async def test_unknown_ticker_has_no_profile(finnhub):
    assert await finnhub.client.profile("ZZZZ") is None


async def test_refusal_and_rate_limit_name_the_endpoint_not_the_key(finnhub):
    finnhub.status["stock/peers"] = 403
    with pytest.raises(FinnhubError) as refused:
        await finnhub.client.peers("NVDA")
    assert refused.value.status == 403 and "stock/peers" in refused.value.message and "secret" not in refused.value.message
    finnhub.status["quote"] = 429
    with pytest.raises(RateLimited):
        await finnhub.client.quote("NVDA")


# ── News ─────────────────────────────────────────────────────────────────────


def test_ibkr_headline_prefix_is_stripped():
    assert news.strip_prefix("{A:800015:L:en}Dow Jones Futures: Apple strong") == "Dow Jones Futures: Apple strong"
    assert news.strip_prefix("Plain headline") == "Plain headline"


def test_merge_is_newest_first_without_repeats():
    a = [{"time": 3, "headline": "Nvidia upgraded at XYZ", "source": "Briefing"}, {"time": 1, "headline": "Old", "source": "DJ"}]
    b = [{"time": 2, "headline": "NVIDIA upgraded at XYZ!", "source": "Reuters"}, {"time": 4, "headline": "New", "source": "Reuters"}]
    assert [i["headline"] for i in news.merge(a, b)] == ["New", "Nvidia upgraded at XYZ", "Old"]


def test_article_html_becomes_text():
    assert news.article_text(0, "<p>First &amp; second</p><p>Third<br/>line</p>") == "First & second\nThird\nline"
    assert news.article_text(1, "JVBERi0=") is None


@pytest.fixture
def ibkr_news(monkeypatch):
    state = SimpleNamespace(connected=True, fail=False)
    news._providers.clear()

    async def providers():
        return [SimpleNamespace(code="BRFUPDN", name="Briefing.com Analyst Actions"), SimpleNamespace(code="DJ-N", name="Dow Jones Global Equity Trader")]

    async def qualify(contract):
        contract.conId = 4815747
        return [contract]

    async def historical(con_id, codes, start, end, total):
        if state.fail:
            raise RuntimeError("boom")
        assert codes == "BRFUPDN+DJ-N" and con_id == 4815747
        return [SimpleNamespace(time=NOW - timedelta(minutes=5), providerCode="BRFUPDN", articleId="BRFUPDN$1", headline="{A:1:L:en}NVDA upgraded to Buy at Example")]

    monkeypatch.setattr(ibkr_service, "get_status", lambda: {"connected": state.connected})
    monkeypatch.setattr(ibkr_service.ibkr, "reqNewsProvidersAsync", providers)
    monkeypatch.setattr(ibkr_service.ibkr, "qualifyContractsAsync", qualify)
    monkeypatch.setattr(ibkr_service.ibkr, "reqHistoricalNewsAsync", historical)
    yield state
    news._providers.clear()


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    yield
    await database._engine.dispose()


@pytest.fixture
def svc(finnhub, ibkr_news, db, monkeypatch):
    service = FundamentalsService()
    monkeypatch.setattr(service, "_client", lambda: finnhub.client)
    return service


# ── Lookup service ───────────────────────────────────────────────────────────


async def test_a_lookup_combines_figures_peers_ratings_and_both_news_sources(svc, finnhub):
    data = await svc.lookup("nvda", now=NOW)
    assert data["ticker"] == "NVDA" and data["industry"] == "Semiconductors" and data["price"] == 182.5
    assert data["peers"] == ["AVGO", "MU", "AMD"]
    pe = next(m for m in data["multiples"] if m["key"] == "pe")
    assert pe["peer_median"] == 60.0 and pe["cheaper_than_peers"] is True
    assert pe["history_median"] == 45.0 and pe["cheaper_than_history"] is True
    assert data["ratings"]["latest"]["total"] == 69
    assert [n["source"] for n in data["news"]] == ["Briefing.com Analyst Actions", "Reuters", "Yahoo"]
    assert data["news"][0]["headline"] == "NVDA upgraded to Buy at Example" and data["news_notes"] == []
    assert data["analysis"] is None
    assert len(finnhub.calls) == 6 + 3  # one metric call per peer


async def test_lookups_are_reused_for_an_hour_unless_refreshed(svc, finnhub):
    await svc.lookup("NVDA", now=NOW)
    await svc.lookup("NVDA", now=NOW + timedelta(minutes=59))
    assert len(finnhub.calls) == 9
    await svc.lookup("NVDA", refresh=True, now=NOW + timedelta(minutes=59))
    await svc.lookup("NVDA", now=NOW + timedelta(minutes=121))
    assert len(finnhub.calls) == 27


async def test_unknown_ticker_and_bad_input(svc):
    with pytest.raises(FundamentalsError) as missing:
        await svc.lookup("ZZZZ", now=NOW)
    assert missing.value.status == 404 and missing.value.code == "not_found"
    with pytest.raises(FundamentalsError) as bad:
        await svc.lookup("../etc", now=NOW)
    assert bad.value.code == "bad_ticker"


async def test_no_finnhub_key_points_to_calendar_settings(monkeypatch, db):
    monkeypatch.setattr(fs, "get_calendar_settings", lambda: SimpleNamespace(finnhub_api_key=""))
    with pytest.raises(FundamentalsError) as err:
        await FundamentalsService().lookup("NVDA", now=NOW)
    assert err.value.code == "no_key" and "Calendar settings" in err.value.message


async def test_rate_limit_is_reported_and_the_cached_figures_survive(svc, finnhub):
    first = await svc.lookup("NVDA", now=NOW)
    finnhub.status["stock/profile2"] = 429
    with pytest.raises(FundamentalsError) as err:
        await svc.lookup("NVDA", refresh=True, now=NOW + timedelta(minutes=5))
    assert err.value.status == 429 and err.value.code == "rate_limited"
    again = await svc.lookup("NVDA", now=NOW + timedelta(minutes=6))
    assert again["fetched_at"] == first["fetched_at"]


async def test_disconnected_ibkr_still_shows_finnhub_news_with_a_note(svc, ibkr_news):
    ibkr_news.connected = False
    data = await svc.lookup("NVDA", now=NOW)
    assert [n["source"] for n in data["news"]] == ["Reuters", "Yahoo"]
    assert data["news_notes"] == ["IBKR news needs a connection to TWS."]


async def test_failing_ibkr_news_does_not_fail_the_lookup(svc, ibkr_news):
    ibkr_news.fail = True
    data = await svc.lookup("NVDA", now=NOW)
    assert data["multiples"] and data["news_notes"] == ["IBKR news couldn't be read."]


# ── AI write-up ──────────────────────────────────────────────────────────────

REPLY = {"bull_case": "Growth.", "bear_case": "Cyclical.", "valuation_view": "Below its history.", "watch": "Margins."}


class FakeProvider:
    name, model = "fake", "fake-model"

    def __init__(self, reply=json.dumps(REPLY), error=None):
        self.reply, self.error, self.calls = reply, error, []

    async def complete(self, system, user, timeout, max_tokens=256, schema=None):
        self.calls.append(json.loads(user))
        self.schema = schema
        if self.error:
            raise self.error
        return self.reply


async def test_write_up_sends_only_public_stock_data_and_is_saved(svc, monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr(fs, "resolve_provider", lambda app, signals: provider)
    saved = await svc.analyze("NVDA")
    sent = provider.calls[0]
    assert set(sent) == {"ticker", "name", "industry", "currency", "price", "market_cap_millions", "multiples", "quality", "peers", "ratings", "headlines"}
    text = json.dumps(sent).lower()
    for word in ("account", "position", "netliquidation", "order", "url"):
        assert word not in text
    assert provider.schema == analysis.SCHEMA
    assert saved["bull_case"] == "Growth." and saved["provider"] == "fake"
    later = await svc.lookup("NVDA")
    assert later["analysis"]["watch"] == "Margins." and later["analysis"]["data_time"] == later["fetched_at"]


@pytest.mark.parametrize("reply", ["not json", json.dumps({"bull_case": "x"}), json.dumps({**REPLY, "bear_case": " "})])
async def test_invalid_write_ups_are_rejected(svc, monkeypatch, reply):
    monkeypatch.setattr(fs, "resolve_provider", lambda app, signals: FakeProvider(reply))
    with pytest.raises(FundamentalsError) as err:
        await svc.analyze("NVDA")
    assert "invalid reply" in err.value.message
    assert await svc.saved_analysis("NVDA") is None


async def test_write_up_without_a_provider(svc, monkeypatch):
    monkeypatch.setattr(fs, "resolve_provider", lambda app, signals: None)
    with pytest.raises(FundamentalsError) as err:
        await svc.analyze("NVDA")
    assert err.value.code == "no_provider" and "Settings" in err.value.message


async def test_provider_errors_hide_their_text(svc, monkeypatch):
    monkeypatch.setattr(fs, "resolve_provider", lambda app, signals: FakeProvider(error=RuntimeError("key=sk-123 leaked")))
    with pytest.raises(FundamentalsError) as err:
        await svc.analyze("NVDA")
    assert err.value.message == "The AI provider failed (RuntimeError)"


# ── API ──────────────────────────────────────────────────────────────────────


async def test_endpoints_return_data_and_errors_with_codes(svc, monkeypatch):
    monkeypatch.setattr(router, "fundamentals_service", svc)
    assert (await router.get_fundamentals("NVDA"))["ticker"] == "NVDA"
    bad = await router.get_fundamentals("a b")
    assert bad.status_code == 422 and json.loads(bad.body)["code"] == "bad_ticker"
    monkeypatch.setattr(fs, "resolve_provider", lambda app, signals: None)
    none = await router.write_analysis("NVDA")
    assert none.status_code == 400 and json.loads(none.body)["code"] == "no_provider"


async def test_article_ids_are_checked(svc, monkeypatch):
    monkeypatch.setattr(router, "fundamentals_service", svc)
    with pytest.raises(router.HTTPException):
        await router.get_article("BRFUPDN", "../../etc")


def test_fundamentals_code_never_touches_orders():
    import backend.fundamentals as pkg
    import pathlib

    sources = [p.read_text() for p in pathlib.Path(pkg.__file__).parent.glob("*.py")] + [pathlib.Path(router.__file__).read_text()]
    for word in ("placeOrder", "cancelOrder", "reqGlobalCancel", "reqAccountSummary", "reqPositions"):
        assert not any(word in s for s in sources)
