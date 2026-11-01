from datetime import datetime, timedelta
from statistics import median
from typing import Iterable, Optional

from backend.signals.analysis import _closes_at, _percent, bars_after

HORIZONS = (5, 15, 30)
WINDOW_MINUTES = HORIZONS[-1]
# A bar can take a moment to publish, so a horizon that just ended waits one more minute.
DUE_AFTER = timedelta(minutes=WINDOW_MINUTES + 1)
MIN_SAMPLE = 30
FIGURES = ("move_5m", "move_15m", "move_30m", "max_up", "max_down")


def measure(bars: list[dict], signal_time: datetime, close_time: datetime) -> Optional[dict]:
    start = signal_time.timestamp()
    # The entry comes from the same fetch as the later bars, because historical bars
    # are split-adjusted and a price saved before a split would show a huge false move.
    entry_bar = next((b for b in bars if _closes_at(b) == start), None)
    if entry_bar is None:
        return None
    entry, end = entry_bar["close"], close_time.timestamp()
    window_end = min(signal_time + timedelta(minutes=WINDOW_MINUTES), close_time)
    later = bars_after(bars, signal_time, window_end)

    def move_at(minutes: int) -> Optional[float]:
        target = start + minutes * 60
        if target > end:
            return None
        reached = [b for b in later if _closes_at(b) <= target]
        return _percent(reached[-1]["close"], entry) if reached else None

    return {
        **{f"move_{m}m": move_at(m) for m in HORIZONS},
        "max_up": max(0.0, _percent(max(b["high"] for b in later), entry)) if later else None,
        "max_down": min(0.0, _percent(min(b["low"] for b in later), entry)) if later else None,
    }


def day_baseline(bars: list[dict], close_time: datetime, tz) -> dict[str, list[float]]:
    series: dict[str, list[float]] = {name: [] for name in FIGURES}
    for bar in bars:
        figures = measure(bars, datetime.fromtimestamp(_closes_at(bar), tz), close_time)
        for name, value in (figures or {}).items():
            if value is not None:
                series[name].append(round(value, 4))
    return series


def _summary(moves: list[float]) -> dict:
    if not moves:
        return {"count": 0, "average": None, "median": None, "up_share": None, "small_sample": True}
    return {
        "count": len(moves),
        "average": sum(moves) / len(moves),
        "median": median(moves),
        "up_share": sum(m > 0 for m in moves) / len(moves),
        "small_sample": len(moves) < MIN_SAMPLE,
    }


def summarize(series: dict[str, list[float]]) -> dict:
    def average(name: str) -> Optional[float]:
        values = series.get(name) or []
        return sum(values) / len(values) if values else None

    return {
        "horizons": {f"{m}m": _summary(series.get(f"move_{m}m") or []) for m in HORIZONS},
        "average_max_up": average("max_up"),
        "average_max_down": average("max_down"),
    }


def collect(rows: Iterable[dict]) -> dict[str, list[float]]:
    series: dict[str, list[float]] = {name: [] for name in FIGURES}
    for row in rows:
        for name in FIGURES:
            if row.get(name) is not None:
                series[name].append(row[name])
    return series
