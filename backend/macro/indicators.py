import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from ib_async import ContFuture, Contract, Index


@dataclass(frozen=True)
class Indicator:
    key: str
    label: str
    unit: str
    change_mode: str  # "pct" for prices, "bp" for yields
    make_contract: Optional[Callable[[], Contract]]
    # CBOE quotes TNX as the yield × 10 (50.98 = 5.098%).
    divisor: float = 1.0
    decimals: int = 2
    source: str = "ibkr"  # or "trm": the official USD/COP rate, which IBKR doesn't offer


INDICATORS: list[Indicator] = [
    Indicator("crude", "Crude oil", "$/bbl", "pct", lambda: ContFuture("CL", "NYMEX")),
    Indicator("gold", "Gold", "$/oz", "pct", lambda: ContFuture("GC", "COMEX")),
    Indicator("es", "S&P 500 futures", "pts", "pct", lambda: ContFuture("ES", "CME")),
    Indicator("nq", "Nasdaq 100 futures", "pts", "pct", lambda: ContFuture("NQ", "CME")),
    Indicator("dow", "Dow futures", "pts", "pct", lambda: ContFuture("YM", "CBOT"), decimals=0),
    Indicator("us10y", "US 10Y yield", "%", "bp", lambda: Index("TNX", "CBOE"), divisor=10.0, decimals=3),
    Indicator("vix", "VIX", "pts", "pct", lambda: Index("VIX", "CBOE")),
    Indicator("usdcop", "USD/COP", "COP", "pct", None, source="trm"),
    # Spot indexes only move during regular hours, so they come after the futures.
    Indicator("spx", "S&P 500", "pts", "pct", lambda: Index("SPX", "CBOE")),
    Indicator("ndx", "Nasdaq 100", "pts", "pct", lambda: Index("NDX", "NASDAQ")),
    Indicator("dji", "Dow Jones", "pts", "pct", lambda: Index("INDU", "CME")),
]


def num(x: Any) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not math.isnan(x) and x > 0 else None


def change_fields(last: Optional[float], prev: Optional[float], mode: str) -> dict:
    if last is None or prev is None:
        return {"change": None, "change_pct": None, "change_bp": None}
    change = last - prev
    return {
        "change": change,
        "change_pct": change / prev * 100 if mode == "pct" else None,
        # Yields are already in percent, so 1 bp is 0.01.
        "change_bp": change * 100 if mode == "bp" else None,
    }


def parse_trading_hours(hours: str, tz_id: str) -> list[tuple[datetime, datetime]]:
    # Futures sessions span midnight ("20261018:1800-20261019:1700"), so these
    # are kept as intervals rather than keyed by date like SessionCalendar.
    tz = ZoneInfo(tz_id or "US/Eastern")
    intervals = []
    # Some products list a day's sessions comma-separated instead of as separate entries.
    for part in filter(None, hours.replace(",", ";").split(";")):
        if part.endswith("CLOSED"):
            continue
        start, _, end = part.partition("-")
        intervals.append(
            (
                datetime.strptime(start, "%Y%m%d:%H%M").replace(tzinfo=tz),
                datetime.strptime(end, "%Y%m%d:%H%M").replace(tzinfo=tz),
            )
        )
    return intervals


def is_open(intervals: list[tuple[datetime, datetime]], now: datetime) -> bool:
    return any(start <= now < end for start, end in intervals)


def freshness(market_open: bool, market_data_type: Optional[int], streaming: bool) -> str:
    if not market_open:
        return "closed"
    # Types 1/2 are real-time, 3/4 delayed. Values from historical bars are
    # never newer than delayed data.
    return "live" if streaming and market_data_type in (1, 2) else "delayed"
