from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from ib_async import Contract, Index, Stock

WINDOW_DAYS = 252
HISTORY_DAYS = 60
MIN_COMPONENTS = 3
BANDS = ((24, "Extreme Fear"), (44, "Fear"), (55, "Neutral"), (75, "Greed"), (100, "Extreme Greed"))

Series = list[Optional[float]]
Closes = dict[str, dict[float, float]]  # symbol -> unix time -> close


def _etf(symbol: str) -> Callable[[], Contract]:
    return lambda: Stock(symbol, "SMART", "USD")


# ETFs use adjusted closes so an income payment doesn't read as a price drop;
# indexes have no adjusted series.
SOURCES: tuple[tuple[str, Callable[[], Contract], str], ...] = (
    ("SPX", lambda: Index("SPX", "CBOE"), "TRADES"),
    ("VIX", lambda: Index("VIX", "CBOE"), "TRADES"),
    ("SPY", _etf("SPY"), "ADJUSTED_LAST"),
    ("TLT", _etf("TLT"), "ADJUSTED_LAST"),
    ("HYG", _etf("HYG"), "ADJUSTED_LAST"),
    ("LQD", _etf("LQD"), "ADJUSTED_LAST"),
    ("RSP", _etf("RSP"), "ADJUSTED_LAST"),
)


def moving_average(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    total = 0.0
    for i, value in enumerate(values):
        total += value
        if i >= period:
            total -= values[i - period]
        if i >= period - 1:
            out[i] = total / period
    return out


def vs_average(values: list[float], period: int) -> Series:
    return [None if avg is None else value / avg - 1 for value, avg in zip(values, moving_average(values, period))]


def period_return(values: list[float], period: int) -> Series:
    return [None if i < period else value / values[i - period] - 1 for i, value in enumerate(values)]


def ratio(top: list[float], bottom: list[float]) -> list[float]:
    return [a / b for a, b in zip(top, bottom)]


def _volatility(vix: list[float]) -> Series:
    # Inverted: a high VIX is fear, so it has to rank low.
    return [None if x is None else -x for x in vs_average(vix, 50)]


def _safe_haven(spy: list[float], tlt: list[float]) -> Series:
    stocks, bonds = period_return(spy, 20), period_return(tlt, 20)
    return [None if a is None or b is None else a - b for a, b in zip(stocks, bonds)]


@dataclass(frozen=True)
class Component:
    key: str
    label: str
    detail: str
    meaning: str
    symbols: tuple[str, ...]
    measure: Callable[..., Series]
    in_score: bool = True


COMPONENTS = (
    Component(
        "momentum",
        "Momentum",
        "S&P 500 vs its 125-day average",
        "High: stocks are well above their six-month trend. Low: they've fallen toward or below it.",
        ("SPX",),
        lambda spx: vs_average(spx, 125),
    ),
    Component(
        "volatility",
        "Volatility",
        "VIX vs its 50-day average, inverted",
        "Inverted, so a VIX below its average scores high (calm) and a VIX above it scores low (fear).",
        ("VIX",),
        _volatility,
    ),
    Component(
        "safe_haven",
        "Safe haven demand",
        "20-day return, SPY minus TLT",
        "High: stocks have beaten long-term Treasuries over the past month. Low: money has favored bonds.",
        ("SPY", "TLT"),
        _safe_haven,
    ),
    Component(
        "junk",
        "Junk bond demand",
        "HYG/LQD vs its 50-day average",
        "High: junk bonds are beating investment-grade bonds, so investors accept more risk. Low: they're getting cautious. "
        "This compares prices, not yield spreads.",
        ("HYG", "LQD"),
        lambda h, l: vs_average(ratio(h, l), 50),
    ),
    Component(
        "breadth",
        "Breadth",
        "RSP/SPY vs its 50-day average",
        "High: the average stock is beating the big companies. Low: a few large stocks lead. "
        "Context only, not in the score: it shows who leads, not whether stocks are rising, so a big-tech sell-off can read high.",
        ("RSP", "SPY"),
        lambda r, s: vs_average(ratio(r, s), 50),
        in_score=False,
    ),
)


def percentile_rank(window: list[float]) -> float:
    return sum(v <= window[-1] for v in window) / len(window) * 100


def component_scores(component: Component, closes: Closes) -> dict[float, float]:
    dates = set.intersection(*(set(closes.get(s, {})) for s in component.symbols))
    times = sorted(dates)
    measured = component.measure(*([closes[s][t] for t in times] for s in component.symbols))
    scores = {}
    for i in range(WINDOW_DAYS - 1, len(times)):
        window = measured[i - WINDOW_DAYS + 1 : i + 1]
        if None not in window:
            scores[times[i]] = percentile_rank(window)
    return scores


def band_for(score: float) -> str:
    rounded = round(score)
    return next(label for top, label in BANDS if rounded <= top)


def build_sentiment(closes: Closes, errors: dict[str, str]) -> dict:
    scored: dict[str, dict[float, float]] = {}
    problems: dict[str, str] = {}
    for component in COMPONENTS:
        missing = [s for s in component.symbols if not closes.get(s)]
        if missing:
            problems[component.key] = next((f"{s}: {errors[s]}" for s in missing if s in errors), f"No data for {', '.join(missing)}")
            continue
        scores = component_scores(component, closes)
        if scores:
            scored[component.key] = scores
        else:
            problems[component.key] = "Not enough history"

    counted = [scored[c.key] for c in COMPONENTS if c.in_score and c.key in scored]
    common = sorted(set.intersection(*(set(s) for s in counted))) if counted else []
    usable = len(counted) >= MIN_COMPONENTS and bool(common)
    average = lambda t: sum(s[t] for s in counted) / len(counted)
    latest = common[-1] if usable else None
    score = average(latest) if usable else None
    return {
        "score": score,
        "band": band_for(score) if score is not None else None,
        "as_of": datetime.fromtimestamp(latest, timezone.utc).date().isoformat() if latest is not None else None,
        "components": [
            {
                "key": c.key,
                "label": c.label,
                "detail": c.detail,
                "meaning": c.meaning,
                "score": scored.get(c.key, {}).get(latest) if usable else None,
                "in_score": c.in_score,
                "error": problems.get(c.key),
            }
            for c in COMPONENTS
        ],
        "history": [{"time": t, "value": average(t)} for t in common[-HISTORY_DAYS:]] if usable else [],
    }
