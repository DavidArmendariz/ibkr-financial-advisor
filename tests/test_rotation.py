from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.rotation import calc, config as rotation_config
from backend.rotation import service as rs
from backend.rotation.service import SECTORS, RotationService, latest_session
from backend.routers import rotation as router
from backend.services import ibkr_service
from backend.signals.sessions import ET

# Friday Nov 6 2026, mid-session.
OPEN = datetime(2026, 11, 6, 11, 0, tzinfo=ET)
AFTER_CLOSE = datetime(2026, 11, 6, 17, 0, tzinfo=ET)


def day(d: date, close: float) -> dict:
    return {"time": datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp(), "close": close}


def weekdays(end: date, n: int) -> list[date]:
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return out[::-1]


# ── Readings ─────────────────────────────────────────────────────────────────


def test_relative_strength_is_the_ratio_of_closes_on_shared_days():
    spy = [day(date(2026, 11, 2), 500), day(date(2026, 11, 3), 400)]
    etf = [day(date(2026, 11, 2), 50), day(date(2026, 11, 3), 50), day(date(2026, 11, 4), 60)]
    assert [v for _, v in calc.relative_strength(etf, spy)] == [10.0, 12.5]


def test_normalise_centres_on_100_after_the_lookback():
    out = calc.normalise([1, 2, 3, 4], lookback=3)
    assert out[:2] == [None, None]
    # The newest of 2,3,4 is one population standard deviation (0.816) above the mean.
    assert out[3] == pytest.approx(100 + 1 / 0.8165, abs=1e-3)
    assert calc.normalise([5, 5, 5], lookback=3)[2] == 100.0


def test_outperforming_and_accelerating_reads_above_100_on_both():
    rs = [(i, 100 + (i * i if i > 12 else 0)) for i in range(25)]
    last = calc.readings(rs)[-1]
    assert last["ratio"] > 100 and last["momentum"] > 100 and last["quadrant"] == calc.LEADING


def test_readings_need_two_lookbacks_of_history():
    assert calc.readings([(i, 100 + i) for i in range(19)]) == []
    assert len(calc.readings([(i, 100 + i % 3) for i in range(20)])) == 1


@pytest.mark.parametrize(
    "ratio,momentum,expected",
    [
        (102, 99, calc.WEAKENING),
        (100, 100, calc.LEADING),
        (100, 99.9, calc.WEAKENING),
        (99.9, 100, calc.IMPROVING),
        (98, 97, calc.LAGGING),
    ],
)
def test_quadrants_split_at_100(ratio, momentum, expected):
    assert calc.quadrant(ratio, momentum) == expected


def test_weeks_end_on_their_last_session():
    # Thu Oct 29 – Fri Nov 6 2026: two weeks, the second ending Friday.
    days = [day(d, i) for i, d in enumerate(weekdays(date(2026, 11, 6), 7))]
    weeks = calc.weekly(days)
    assert [datetime.fromtimestamp(w["time"], timezone.utc).date() for w in weeks] == [
        date(2026, 10, 30),
        date(2026, 11, 6),
    ]
    assert weeks[-1]["close"] == 6


def test_a_holiday_friday_ends_the_week_on_thursday():
    days = [day(date(2026, 11, 2), 1), day(date(2026, 11, 5), 2), day(date(2026, 11, 9), 3)]
    assert [w["close"] for w in calc.weekly(days)] == [2, 3]


def test_periods_in_quadrant_counts_the_current_run():
    q = lambda *names: [{"quadrant": n} for n in names]  # noqa: E731
    assert calc.periods_in_quadrant(q("Lagging", "Improving", "Improving")) == 2
    assert calc.periods_in_quadrant(q("Leading")) == 1
    assert calc.periods_in_quadrant([]) == 0


def test_latest_session_waits_for_the_close_and_skips_weekends():
    assert latest_session(OPEN) == date(2026, 11, 5)
    assert latest_session(AFTER_CLOSE) == date(2026, 11, 6)
    assert latest_session(datetime(2026, 11, 8, 12, 0, tzinfo=ET)) == date(2026, 11, 6)
    assert latest_session(datetime(2026, 11, 9, 9, 0, tzinfo=ET)) == date(2026, 11, 6)


def test_settings_validate_before_saving(monkeypatch):
    saved = {}
    monkeypatch.setattr(rotation_config, "save_env_values", saved.update)
    monkeypatch.delenv("ROTATION_TAIL", raising=False)
    rotation_config.get_rotation_settings.cache_clear()
    with pytest.raises(Exception):
        rotation_config.save_rotation_settings({"tail": 25})
    assert saved == {}
    rotation_config.save_rotation_settings({"tail": 12, "timeframe": "daily"})
    assert saved == {"ROTATION_TAIL": "12", "ROTATION_TIMEFRAME": "daily"}
    rotation_config.get_rotation_settings.cache_clear()


# ── Service ──────────────────────────────────────────────────────────────────

DAYS = weekdays(date(2026, 11, 6), 300)


@pytest.fixture
def world(monkeypatch):
    state = SimpleNamespace(connected=True, requests=[], refuse=set(), empty=set(), service=None)
    con_ids = {s: i + 1 for i, s in enumerate(["SPY", *[s for s, _ in SECTORS]])}

    async def qualify(contract):
        if contract.symbol in state.refuse:
            return []
        contract.conId = con_ids[contract.symbol]
        return [contract]

    async def bars(contract, duration, size, what, rth):
        state.requests.append(contract.symbol)
        if contract.symbol in state.empty:
            state.service._on_error(9, 162, "No market data permissions", contract)
            return []
        drift = 0 if contract.symbol == "SPY" else con_ids[contract.symbol]
        return [day(d, 100 + i * 0.1 + (i % 7) * drift * 0.05) for i, d in enumerate(DAYS)]

    monkeypatch.setattr(ibkr_service, "get_status", lambda: {"connected": state.connected})
    monkeypatch.setattr(ibkr_service.ibkr, "qualifyContractsAsync", qualify)
    monkeypatch.setattr(ibkr_service, "get_historical_bars", bars)
    state.service = RotationService()
    return state


async def test_a_refresh_reads_every_etf_against_spy(world):
    await world.service.tick(AFTER_CLOSE)
    state = world.service.state()
    assert world.requests[0] == "SPY" and len(world.requests) == 13
    assert len(state["etfs"]) == 12 and state["etfs"][1]["symbol"] == "SMH"
    weekly, daily = state["etfs"][0]["weekly"], state["etfs"][0]["daily"]
    assert len(weekly["points"]) == 20 and len(daily["points"]) == 20 and weekly["periods"] >= 1
    assert {"time", "ratio", "momentum", "quadrant"} <= set(daily["points"][-1])


async def test_bars_are_fetched_once_per_session(world):
    await world.service.tick(AFTER_CLOSE)
    await world.service.tick(AFTER_CLOSE + timedelta(hours=2))
    assert len(world.requests) == 13
    await world.service.tick(AFTER_CLOSE + timedelta(days=3))
    assert len(world.requests) == 26


async def test_todays_partial_bar_is_left_out(world):
    await world.service.tick(OPEN)
    last = world.service.state()["last_session"]
    assert datetime.fromtimestamp(last, timezone.utc).date() == date(2026, 11, 5)


async def test_a_refused_etf_shows_its_error_and_the_others_plot(world):
    world.empty.add("XLRE")
    await world.service.tick(AFTER_CLOSE)
    rows = {r["symbol"]: r for r in world.service.state()["etfs"]}
    assert rows["XLRE"]["error"].startswith("IBKR error 162") and rows["XLRE"]["daily"]["points"] == []
    assert rows["XLK"]["error"] is None and rows["XLK"]["daily"]["points"]


async def test_only_the_failed_etf_is_asked_again(world):
    world.refuse.add("XLRE")
    await world.service.tick(AFTER_CLOSE)
    assert world.service.state()["etfs"][-1]["error"] == "IBKR has no contract for this"
    world.refuse.clear()
    world.requests.clear()
    await world.service.tick(AFTER_CLOSE + timedelta(minutes=1))
    assert world.requests == []
    await world.service.tick(AFTER_CLOSE + timedelta(minutes=6))
    assert world.requests == ["XLRE"]


async def test_missing_spy_says_so(world):
    world.empty.add("SPY")
    await world.service.tick(AFTER_CLOSE)
    state = world.service.state()
    assert state["benchmark"]["error"].startswith("IBKR error 162")
    assert all(r["weekly"]["points"] == [] for r in state["etfs"])


async def test_a_failed_refresh_keeps_the_last_readings(world):
    await world.service.tick(AFTER_CLOSE)
    before = world.service.state()["etfs"][0]["daily"]["points"]
    world.empty.add("XLK")
    await world.service.tick(AFTER_CLOSE + timedelta(days=3))
    row = world.service.state()["etfs"][0]
    assert row["daily"]["points"] == before and row["error"]


async def test_disconnected_keeps_readings_marked_stale(world):
    await world.service.tick(AFTER_CLOSE)
    world.connected = False
    world.requests.clear()
    await world.service.tick(AFTER_CLOSE + timedelta(days=3))
    state = world.service.state()
    assert world.requests == [] and state["stale"] and state["etfs"][0]["weekly"]["points"]


async def test_endpoint_returns_readings_and_settings(world, monkeypatch):
    monkeypatch.setattr(router, "rotation_service", world.service)
    await world.service.tick(AFTER_CLOSE)
    body = await router.get_rotation()
    assert body["settings"]["tail"] in range(3, 21) and body["lookback"] == 10
    assert len(body["etfs"]) == 12


async def test_settings_endpoint_rejects_unknown_and_invalid(monkeypatch):
    monkeypatch.setattr(rotation_config, "save_env_values", lambda values: None)
    rotation_config.get_rotation_settings.cache_clear()
    with pytest.raises(router.HTTPException) as unknown:
        await router.update_settings({"benchmark": "QQQ"})
    assert unknown.value.status_code == 422
    with pytest.raises(router.HTTPException) as invalid:
        await router.update_settings({"tail": 2})
    assert "tail" in invalid.value.detail
    rotation_config.get_rotation_settings.cache_clear()


def test_the_service_never_touches_orders():
    source = open(rs.__file__).read()
    assert not any(word in source for word in ("placeOrder", "cancelOrder", "reqGlobalCancel"))
