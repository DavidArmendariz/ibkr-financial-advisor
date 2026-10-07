import random
from datetime import datetime, timedelta

import pandas as pd
import pytest

from backend.signals.indicators import EMA, Bollinger, RelativeVolume, SessionVWAP
from backend.signals.models import Bar
from backend.signals.sessions import ET, SessionCalendar


def series(n=300, seed=7):
    rng = random.Random(seed)
    price, out = 40.0, []
    for _ in range(n):
        price = max(1.0, price + rng.gauss(0, 0.3))
        out.append(round(price, 4))
    return out


def volumes(n=300, seed=11):
    rng = random.Random(seed)
    return [float(rng.randint(1_000, 50_000)) for _ in range(n)]


def test_ema_hand_computed():
    ema = EMA(3)  # alpha = 0.5
    assert [ema.update(x) for x in [1, 2, 3, 4]] == [None, None, 2.25, 3.125]


@pytest.mark.parametrize("period", [9, 21])
def test_ema_matches_pandas(period):
    closes = series()
    ref = pd.Series(closes).ewm(span=period, adjust=False).mean()
    ema = EMA(period)
    got = [ema.update(x) for x in closes]
    for i, value in enumerate(got):
        if i < period - 1:
            assert value is None
        else:
            assert value == pytest.approx(ref[i], rel=1e-12)


def test_bollinger_matches_pandas():
    closes = series()
    s = pd.Series(closes)
    mid = s.rolling(20).mean()
    std = s.rolling(20).std(ddof=0)
    bb = Bollinger(20, 2.0)
    for i, x in enumerate(closes):
        out = bb.update(x)
        if i < 19:
            assert out is None
        else:
            assert out[0] == pytest.approx(mid[i], rel=1e-9)
            assert out[1] == pytest.approx(mid[i] + 2 * std[i], rel=1e-9)
            assert out[2] == pytest.approx(mid[i] - 2 * std[i], rel=1e-9)


def test_relative_volume_matches_pandas():
    vols = volumes()
    ref = pd.Series(vols) / pd.Series(vols).shift(1).rolling(20).mean()
    rv = RelativeVolume(20)
    for i, v in enumerate(vols):
        out = rv.update(v)
        if i < 20:
            assert out is None
        else:
            assert out == pytest.approx(ref[i], rel=1e-9)


def session_bars(day, n, closes, vols, start=(9, 30)):
    t0 = datetime(day.year, day.month, day.day, *start, tzinfo=ET)
    return [
        Bar(t0 + timedelta(minutes=i), c - 0.1, c + 0.2, c - 0.3, c, v)
        for i, (c, v) in enumerate(zip(closes[:n], vols[:n]))
    ]


def test_vwap_matches_pandas_and_resets_each_session():
    cal = SessionCalendar()
    closes, vols = series(), volumes()
    day1 = session_bars(datetime(2026, 10, 1), 120, closes, vols)
    day2 = session_bars(datetime(2026, 10, 2), 120, closes[120:], vols[120:])
    bars = day1 + day2
    df = pd.DataFrame(
        {
            "day": [b.time.date() for b in bars],
            "pv": [(b.high + b.low + b.close) / 3 * b.volume for b in bars],
            "v": [b.volume for b in bars],
        }
    )
    ref = df.groupby("day")["pv"].cumsum() / df.groupby("day")["v"].cumsum()
    vwap = SessionVWAP(lambda t: cal.vwap_anchor(t, include_premarket=False))
    for i, bar in enumerate(bars):
        assert vwap.update(bar) == pytest.approx(ref[i], rel=1e-12)


def test_vwap_ignores_premarket_unless_included():
    cal = SessionCalendar()
    premarket = Bar(datetime(2026, 10, 1, 9, 0, tzinfo=ET), 10, 10, 10, 10, 1000)
    regular = Bar(datetime(2026, 10, 1, 9, 30, tzinfo=ET), 20, 20, 20, 20, 1000)

    rth_only = SessionVWAP(lambda t: cal.vwap_anchor(t, include_premarket=False))
    assert rth_only.update(premarket) is None
    assert rth_only.update(regular) == pytest.approx(20)

    with_pre = SessionVWAP(lambda t: cal.vwap_anchor(t, include_premarket=True))
    assert with_pre.update(premarket) == pytest.approx(10)
    assert with_pre.update(regular) == pytest.approx(15)
