from datetime import datetime, timedelta, timezone

from backend.signals.bars import BarAggregator


def t(minute, second=0):
    return datetime(2026, 10, 1, 14, minute, second, tzinfo=timezone.utc)


def feed_minute(agg, minute, base=10.0, skip=()):
    out = []
    for i in range(12):
        if i in skip:
            continue
        price = base + i * 0.01
        out.append(agg.add(t(minute, i * 5), price, price + 0.05, price - 0.05, price + 0.01, 100))
    return [b for b in out if b]


def test_full_minute_emits_one_bar_on_its_last_five_second_bar():
    agg = BarAggregator(1)
    bars = feed_minute(agg, 30)
    assert len(bars) == 1
    bar = bars[0]
    assert bar.time == t(30)
    assert bar.open == 10.0
    assert abs(bar.high - 10.16) < 1e-9
    assert abs(bar.low - 9.95) < 1e-9
    assert abs(bar.close - 10.12) < 1e-9
    assert bar.volume == 1200


def test_bucket_joined_midway_is_dropped():
    agg = BarAggregator(1)
    first = [agg.add(t(30, s), 10, 10, 10, 10, 1) for s in range(20, 60, 5)]
    assert not any(first)
    assert len(feed_minute(agg, 31)) == 1


def test_gap_inside_bucket_drops_it():
    agg = BarAggregator(1)
    assert feed_minute(agg, 30, skip={4}) == []
    assert len(feed_minute(agg, 31)) == 1


def test_five_minute_buckets():
    agg = BarAggregator(5)
    emitted = []
    for minute in range(30, 40):
        emitted += feed_minute(agg, minute)
    assert [b.time for b in emitted] == [t(30), t(35)]
    assert all(b.volume == 6000 for b in emitted)
    assert emitted[1].time - emitted[0].time == timedelta(minutes=5)
