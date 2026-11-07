import statistics
from datetime import datetime, timezone
from typing import Optional

LOOKBACK = 10
LEADING, WEAKENING, LAGGING, IMPROVING = "Leading", "Weakening", "Lagging", "Improving"
QUADRANTS = [LEADING, WEAKENING, LAGGING, IMPROVING]


def _day(bar: dict):
    return datetime.fromtimestamp(bar["time"], timezone.utc).date()


def weekly(bars: list[dict]) -> list[dict]:
    # Each week's reading is its last session's close, normally Friday's.
    out: list[dict] = []
    for bar in bars:
        week = _day(bar).isocalendar()[:2]
        if out and _day(out[-1]).isocalendar()[:2] == week:
            out[-1] = bar
        else:
            out.append(bar)
    return out


def relative_strength(etf: list[dict], spy: list[dict]) -> list[tuple[float, float]]:
    spy_close = {b["time"]: b["close"] for b in spy}
    return [(b["time"], 100 * b["close"] / spy_close[b["time"]]) for b in etf if spy_close.get(b["time"])]


def normalise(values: list[float], lookback: int = LOOKBACK) -> list[Optional[float]]:
    # 100 plus how many standard deviations the value sits from its recent mean.
    out: list[Optional[float]] = [None] * len(values)
    for i in range(lookback - 1, len(values)):
        window = values[i - lookback + 1 : i + 1]
        sd = statistics.pstdev(window)
        out[i] = 100.0 if sd == 0 else 100 + (values[i] - statistics.mean(window)) / sd
    return out


def readings(rs: list[tuple[float, float]], lookback: int = LOOKBACK) -> list[dict]:
    ratio = normalise([v for _, v in rs], lookback)
    start = next((i for i, r in enumerate(ratio) if r is not None), len(ratio))
    change = [ratio[i] - ratio[i - 1] for i in range(start + 1, len(ratio))]
    momentum = normalise(change, lookback)
    out = []
    for j, m in enumerate(momentum):
        if m is None:
            continue
        i = start + 1 + j
        out.append({"time": rs[i][0], "ratio": ratio[i], "momentum": m, "quadrant": quadrant(ratio[i], m)})
    return out


def quadrant(ratio: float, momentum: float) -> str:
    if ratio >= 100:
        return LEADING if momentum >= 100 else WEAKENING
    return IMPROVING if momentum >= 100 else LAGGING


def periods_in_quadrant(points: list[dict]) -> int:
    if not points:
        return 0
    current, count = points[-1]["quadrant"], 0
    for p in reversed(points):
        if p["quadrant"] != current:
            break
        count += 1
    return count
