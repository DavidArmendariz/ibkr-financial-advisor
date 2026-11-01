import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from backend import database
from backend.calendar_events import config as calendar_config
from backend.calendar_events import service as module
from backend.calendar_events import sources
from backend.calendar_events.config import CalendarSettings, public_settings
from backend.calendar_events.service import CalendarService, alert_due, alert_times
from backend.calendar_events.sources import ET, Event, SourceError, parse_earnings, parse_fomc, parse_fred
from backend.database import CalendarEvent

TODAY = date(2026, 11, 2)
NOW = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
FOMC_HTML = """
<h4>2026 FOMC Meetings</h4>
<div class="fomc-meeting__month col-xs-5"><strong>October</strong></div><div class="fomc-meeting__date col-xs-4">27-28</div>
<div class="fomc-meeting__month col-xs-5"><strong>December</strong></div><div class="fomc-meeting__date col-xs-4">8-9*</div>
<h4>2027 FOMC Meetings</h4>
<div class="fomc-meeting__month col-xs-5"><strong>Apr/May</strong></div><div class="fomc-meeting__date col-xs-4">30-1</div>
<h4>2025 FOMC Meetings</h4>
<div class="fomc-meeting__month col-xs-5"><strong>June</strong></div><div class="fomc-meeting__date col-xs-4">17-18</div>
"""


def et(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=ET).astimezone(timezone.utc)


def row(id_="fomc:2026-11-03", source="fomc", importance="high", category="economic", day="2026-11-03", at=None, timing=None, name="FOMC decision"):
    return CalendarEvent(id=id_, source=source, name=name, category=category, importance=importance, day=day, at=at, timing=timing, fetched_at=NOW)


def test_fred_uses_the_releases_usual_time_and_drops_past_dates():
    events = parse_fred(10, {"release_dates": [{"date": "2026-10-14"}, {"date": "2026-11-10"}]}, TODAY)
    assert [(e.name, e.importance, e.day) for e in events] == [("CPI", "high", date(2026, 11, 10))]
    assert events[0].at == et(2026, 11, 10, 8, 30)


def test_medium_importance_release():
    assert parse_fred(46, {"release_dates": [{"date": "2026-11-13"}]}, TODAY)[0].importance == "medium"


def test_fomc_uses_the_last_day_at_two_pm():
    events = parse_fomc(FOMC_HTML, TODAY)
    assert [e.day for e in events] == [date(2026, 12, 9), date(2027, 5, 1)]
    assert events[0].at == et(2026, 12, 9, 14)
    assert events[0].importance == "high"


def test_unexpected_fed_page_is_an_error():
    with pytest.raises(SourceError):
        parse_fomc("<html>redesigned</html>", TODAY)


def test_earnings_timing():
    payload = {"earningsCalendar": [{"symbol": "NVDA", "date": "2026-11-17", "hour": "amc"}, {"symbol": "TSM", "date": "2026-11-18", "hour": "bmo"}, {"symbol": "LRCX", "date": "2026-11-19", "hour": ""}]}
    events = parse_earnings(payload, TODAY)
    assert [(e.name, e.timing, e.at) for e in events] == [("NVDA earnings", "after_close", None), ("TSM earnings", "before_open", None), ("LRCX earnings", None, None)]


def test_watchlist_is_cleaned():
    assert CalendarSettings.model_construct(earnings_symbols=" nvda, AMD,,nvda ").symbols() == ["NVDA", "AMD"]


def test_keys_are_never_public():
    secret = "abcd1234efgh5678"
    settings = CalendarSettings.model_construct(fred_api_key=secret, finnhub_api_key="", earnings_symbols="NVDA", alert_evening_enabled=True, alert_soon_enabled=True)
    public = json.dumps(public_settings(settings), ensure_ascii=False)
    assert secret not in public and "…5678" in public
    assert public_settings(settings)["finnhub_key_set"] is False


async def test_network_errors_never_carry_the_key():
    def fail(request):
        raise httpx.ConnectError(f"failed {request.url}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(SourceError) as err:
            await sources.fetch_earnings(client, "SECRETKEY", ["NVDA"], TODAY)
    assert "SECRETKEY" not in str(err.value)


async def test_earnings_requests_each_symbol_separately():
    seen = []

    def reply(request):
        seen.append(request.url.params["symbol"])
        return httpx.Response(200, json={"earningsCalendar": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
        await sources.fetch_earnings(client, "k", ["NVDA", "AMD"], TODAY)
    assert seen == ["NVDA", "AMD"]


def finnhub_reply(request):
    symbol = request.url.params["symbol"]
    if symbol == "005930.KS":
        return httpx.Response(403, json={"error": "no access"})
    return httpx.Response(200, json={"earningsCalendar": [{"symbol": symbol, "date": "2026-11-17", "hour": "amc"}]})


async def test_a_refused_symbol_costs_only_itself():
    async with httpx.AsyncClient(transport=httpx.MockTransport(finnhub_reply)) as client:
        events, refused = await sources.fetch_earnings(client, "k", ["NVDA", "005930.KS", "AMD"], TODAY)
    assert [e.name for e in events] == ["NVDA earnings", "AMD earnings"]
    assert refused == ["005930.KS"]


async def test_every_symbol_refused_is_an_error():
    async with httpx.AsyncClient(transport=httpx.MockTransport(finnhub_reply)) as client:
        with pytest.raises(SourceError):
            await sources.fetch_earnings(client, "k", ["005930.KS"], TODAY)


async def test_http_errors_are_readable():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(429))) as client:
        with pytest.raises(SourceError) as err:
            await sources.fetch_fomc(client, TODAY)
    assert "429" in str(err.value)


def test_high_importance_with_a_time_gets_both_alerts():
    times = dict(alert_times(row(at=et(2026, 11, 3, 14))))
    assert times["evening"] == et(2026, 11, 2, 18)
    assert times["soon"] == et(2026, 11, 3, 13, 30)


def test_earnings_without_a_time_gets_only_the_evening_alert():
    event = row(category="earnings", importance="medium", timing="after_close")
    assert [k for k, _ in alert_times(event)] == ["evening"]


def test_medium_economic_event_gets_no_alert():
    assert alert_times(row(importance="medium", at=et(2026, 11, 3, 8, 30))) == []


def test_alert_window():
    event = row(at=et(2026, 11, 3, 14))
    when = et(2026, 11, 2, 18)
    assert alert_due(when, event, when + timedelta(minutes=29))
    assert not alert_due(when, event, when - timedelta(minutes=1))
    assert not alert_due(when, event, when + timedelta(minutes=30))  # missed: skipped
    assert not alert_due(et(2026, 11, 3, 13, 30), event, et(2026, 11, 3, 14, 1))  # the event has passed


@pytest.fixture
async def world(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "AsyncSessionLocal", None)
    await database.create_db_and_tables()
    state = SimpleNamespace(
        settings=CalendarSettings.model_construct(fred_api_key="f", finnhub_api_key="g", earnings_symbols="NVDA", alert_evening_enabled=True, alert_soon_enabled=True),
        sent=[],
    )
    monkeypatch.setattr(module, "get_calendar_settings", lambda: state.settings)
    state.service = CalendarService(broadcast=state.sent.append)
    yield state
    await database._engine.dispose()


def event(day=date(2026, 11, 3), at=None, id_="fomc:x", source="fomc", importance="high", name="FOMC decision"):
    return Event(id_, source, name, "economic", importance, day, at)


async def test_state_lists_soonest_first_within_30_days(world):
    await world.service._save("fomc", [event(date(2026, 11, 20), et(2026, 11, 20, 14), "a"), event(date(2026, 11, 3), et(2026, 11, 3, 14), "b"), event(date(2027, 1, 5), et(2027, 1, 5, 14), "c")], NOW)
    state = await world.service.state(NOW)
    assert [e["id"] for e in state["events"]] == ["b", "a"]


async def test_an_event_that_has_passed_today_leaves_the_list(world):
    await world.service._save("fomc", [event(date(2026, 11, 2), et(2026, 11, 2, 8, 30), "past")], NOW)
    assert (await world.service.state(NOW))["events"] == []


async def test_failed_source_keeps_its_events_and_retries(world, monkeypatch):
    await world.service._save("fomc", [event(at=et(2026, 11, 3, 14))], NOW)

    async def fail(client, today):
        raise SourceError("The Federal Reserve site returned HTTP 500")

    async def empty(*args):
        return []

    async def no_earnings(*args):
        return [], []

    monkeypatch.setattr(sources, "fetch_fomc", fail)
    monkeypatch.setattr(sources, "fetch_fred", empty)
    monkeypatch.setattr(sources, "fetch_earnings", no_earnings)
    await world.service.refresh_due(NOW)
    state = await world.service.state(NOW)
    assert len(state["events"]) == 1
    fomc = next(s for s in state["sources"] if s["key"] == "fomc")
    assert "HTTP 500" in fomc["error"] and fomc["updated_at"]
    assert world.service.next_refresh["fomc"] == NOW + timedelta(hours=1)


async def test_refused_symbols_are_reported_and_the_rest_save(world, monkeypatch):
    async def fomc(client, today):
        return []

    async def fred(*args):
        return []

    async def earnings(*args):
        return [event(id_="finnhub:NVDA", source="finnhub", name="NVDA earnings")], ["005930.KS"]

    monkeypatch.setattr(sources, "fetch_fomc", fomc)
    monkeypatch.setattr(sources, "fetch_fred", fred)
    monkeypatch.setattr(sources, "fetch_earnings", earnings)
    await world.service.refresh_due(NOW)
    state = await world.service.state(NOW)
    assert [e["name"] for e in state["events"]] == ["NVDA earnings"]
    assert "005930.KS" in next(s for s in state["sources"] if s["key"] == "finnhub")["error"]
    assert world.service.next_refresh["finnhub"] == NOW + timedelta(hours=6)


async def test_missing_key_only_affects_its_source(world, monkeypatch):
    world.settings.fred_api_key = ""
    called = []

    async def fomc(client, today):
        called.append("fomc")
        return [event(at=et(2026, 11, 3, 14))]

    async def fred(*args):
        called.append("fred")
        return []

    async def earnings(*args):
        called.append("finnhub")
        return [], []

    monkeypatch.setattr(sources, "fetch_fomc", fomc)
    monkeypatch.setattr(sources, "fetch_fred", fred)
    monkeypatch.setattr(sources, "fetch_earnings", earnings)
    await world.service.refresh_due(NOW)
    assert "fred" not in called and {"fomc", "finnhub"} <= set(called)
    state = await world.service.state(NOW)
    assert next(s for s in state["sources"] if s["key"] == "fred")["configured"] is False
    assert len(state["events"]) == 1


async def test_refresh_waits_six_hours(world, monkeypatch):
    calls = []

    async def fomc(client, today):
        calls.append(1)
        return []

    async def empty(*args):
        return []

    async def no_earnings(*args):
        return [], []

    monkeypatch.setattr(sources, "fetch_fomc", fomc)
    monkeypatch.setattr(sources, "fetch_fred", empty)
    monkeypatch.setattr(sources, "fetch_earnings", no_earnings)
    await world.service.refresh_due(NOW)
    await world.service.refresh_due(NOW + timedelta(hours=5))
    assert len(calls) == 1
    await world.service.refresh_due(NOW + timedelta(hours=6))
    assert len(calls) == 2


async def test_alert_fires_once_across_restarts(world):
    await world.service._save("fomc", [event(at=et(2026, 11, 3, 14))], NOW)
    when = et(2026, 11, 2, 18, 1)
    await world.service.send_alerts(when)
    await world.service.send_alerts(when)
    restarted = CalendarService(broadcast=world.sent.append)
    await restarted.send_alerts(when)
    assert len(world.sent) == 1
    assert world.sent[0]["alert"] == "evening" and world.sent[0]["event"]["name"] == "FOMC decision"


async def test_each_switch_stops_its_alert(world):
    await world.service._save("fomc", [event(at=et(2026, 11, 3, 14))], NOW)
    world.settings.alert_evening_enabled = False
    await world.service.send_alerts(et(2026, 11, 2, 18, 1))
    assert world.sent == []
    world.settings.alert_soon_enabled = False
    await world.service.send_alerts(et(2026, 11, 3, 13, 31))
    assert world.sent == []
    world.settings.alert_soon_enabled = True
    await world.service.send_alerts(et(2026, 11, 3, 13, 31))
    assert [s["alert"] for s in world.sent] == ["soon"]


async def test_a_rescheduled_event_can_alert_again(world):
    await world.service._save("fomc", [event(at=et(2026, 11, 3, 14))], NOW)
    await world.service.send_alerts(et(2026, 11, 3, 13, 31))
    await world.service._save("fomc", [event(at=et(2026, 11, 3, 15))], NOW)
    await world.service.send_alerts(et(2026, 11, 3, 14, 31))
    assert [s["alert"] for s in world.sent] == ["soon", "soon"]


async def test_saved_events_survive_a_restart(world):
    await world.service._save("fomc", [event(at=et(2026, 11, 3, 14))], NOW)
    assert len((await CalendarService().state(NOW))["events"]) == 1


def test_save_settings_clears_the_cache(monkeypatch):
    saved = {}
    monkeypatch.setattr(calendar_config, "save_env_values", saved.update)
    calendar_config.get_calendar_settings.cache_clear()
    calendar_config.save_calendar_settings({"earnings_symbols": "NVDA", "alert_soon_enabled": False})
    assert saved == {"CALENDAR_EARNINGS_SYMBOLS": "NVDA", "CALENDAR_ALERT_SOON_ENABLED": "false"}
    calendar_config.get_calendar_settings.cache_clear()
