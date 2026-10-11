import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Iterable, Optional

from backend.signals.sessions import ET

SECONDS_PER_YEAR = 365.0 * 24 * 3600
MIN_YEARS = 1.0 / (365 * 24)  # an hour; keeps expiring options finite


@dataclass(frozen=True)
class OptionRow:
    expiry: date
    strike: float
    right: str  # "C" | "P"
    open_interest: float
    gamma: Optional[float]  # per share, from IBKR's model greeks
    iv: Optional[float]
    multiplier: float = 100.0


def years_to_expiry(expiry: date, now: datetime) -> float:
    close = datetime.combine(expiry, time(16, 0), ET)
    return max((close - now).total_seconds() / SECONDS_PER_YEAR, MIN_YEARS)


def bs_gamma(spot: float, strike: float, years: float, iv: float, rate: float = 0.0) -> float:
    if spot <= 0 or strike <= 0 or years <= 0 or iv <= 0:
        return 0.0
    sqrt_t = math.sqrt(years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv * iv) * years) / (iv * sqrt_t)
    return math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (spot * iv * sqrt_t)


def dollar_gamma(row: OptionRow, spot: float, gamma: Optional[float] = None) -> float:
    # Dollar change in dealer delta for a 1% move in the underlying. Calls count
    # positive and puts negative (dealers assumed long calls, short puts).
    g = row.gamma if gamma is None else gamma
    if not g or not row.open_interest:
        return 0.0
    sign = 1.0 if row.right == "C" else -1.0
    return sign * g * row.open_interest * row.multiplier * spot * spot * 0.01


@dataclass
class StrikeExposure:
    strike: float
    call: float = 0.0
    put: float = 0.0
    call_oi: float = 0.0
    put_oi: float = 0.0

    @property
    def net(self) -> float:
        return self.call + self.put


def by_strike(rows: Iterable[OptionRow], spot: float) -> list[StrikeExposure]:
    out: dict[float, StrikeExposure] = {}
    for r in rows:
        s = out.setdefault(r.strike, StrikeExposure(r.strike))
        gex = dollar_gamma(r, spot)
        if r.right == "C":
            s.call += gex
            s.call_oi += r.open_interest
        else:
            s.put += gex
            s.put_oi += r.open_interest
    return sorted(out.values(), key=lambda s: s.strike)


def by_expiry(rows: Iterable[OptionRow], spot: float) -> list[dict]:
    out: dict[date, dict] = defaultdict(lambda: {"call": 0.0, "put": 0.0, "call_oi": 0.0, "put_oi": 0.0})
    for r in rows:
        e = out[r.expiry]
        gex = dollar_gamma(r, spot)
        if r.right == "C":
            e["call"] += gex
            e["call_oi"] += r.open_interest
        else:
            e["put"] += gex
            e["put_oi"] += r.open_interest
    return [{"expiry": k, **v, "net": v["call"] + v["put"]} for k, v in sorted(out.items())]


def net_gex_at(rows: list[OptionRow], spot: float, now: datetime, rate: float = 0.0) -> float:
    # Re-prices every option's gamma at a hypothetical spot from its own IV.
    return sum(
        dollar_gamma(r, spot, bs_gamma(spot, r.strike, years_to_expiry(r.expiry, now), r.iv, rate))
        for r in rows
        if r.iv
    )


def zero_gamma_level(
    rows: list[OptionRow], spot: float, now: datetime, rate: float = 0.0, span: float = 0.3, steps: int = 120
) -> Optional[float]:
    # The spot price where net exposure changes sign, nearest to the current price.
    lo, hi = spot * (1 - span), spot * (1 + span)
    grid = [lo + (hi - lo) * i / steps for i in range(steps + 1)]
    values = [net_gex_at(rows, s, now, rate) for s in grid]
    crossings = []
    for (s0, v0), (s1, v1) in zip(zip(grid, values), zip(grid[1:], values[1:])):
        if v0 == 0:
            crossings.append(s0)
        elif v0 * v1 < 0:
            crossings.append(s0 + (s1 - s0) * (-v0) / (v1 - v0))
    return min(crossings, key=lambda s: abs(s - spot)) if crossings else None


def summarize(rows: list[OptionRow], spot: float, now: datetime, rate: float = 0.0) -> dict:
    strikes = by_strike(rows, spot)
    calls = [s for s in strikes if s.call > 0]
    puts = [s for s in strikes if s.put < 0]
    total_call = sum(s.call for s in strikes)
    total_put = sum(s.put for s in strikes)
    return {
        "spot": spot,
        "net_gex": total_call + total_put,
        "call_gex": total_call,
        "put_gex": total_put,
        "call_wall": max(calls, key=lambda s: s.call).strike if calls else None,
        "put_wall": min(puts, key=lambda s: s.put).strike if puts else None,
        "zero_gamma": zero_gamma_level(rows, spot, now, rate),
        "strikes": [
            {"strike": s.strike, "call": s.call, "put": s.put, "net": s.net, "call_oi": s.call_oi, "put_oi": s.put_oi}
            for s in strikes
        ],
        "expiries": [{**e, "expiry": e["expiry"].isoformat()} for e in by_expiry(rows, spot)],
        "contracts": len(rows),
    }
