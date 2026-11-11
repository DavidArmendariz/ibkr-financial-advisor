from typing import Optional


def shift_month(month: str, months: int) -> str:
    year, mon = int(month[:4]), int(month[5:7])
    index = year * 12 + (mon - 1) + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}-01"


def pct(now: float, before: Optional[float]) -> Optional[float]:
    if before is None or before == 0:
        return None
    return (now / before - 1) * 100


def with_growth(observations: list[tuple[str, float]]) -> list[dict]:
    by_month = dict(observations)
    return [{"month": m, "value": v, "yoy_pct": pct(v, by_month.get(shift_month(m, -12)))} for m, v in observations]


def latest_reading(observations: list[tuple[str, float]]) -> Optional[dict]:
    if not observations:
        return None
    by_month = dict(observations)
    month, value = observations[-1]
    prev = by_month.get(shift_month(month, -1))
    year_ago = by_month.get(shift_month(month, -12))
    return {
        "month": month,
        "value": value,
        "mom_change": None if prev is None else value - prev,
        "mom_pct": pct(value, prev),
        "yoy_change": None if year_ago is None else value - year_ago,
        "yoy_pct": pct(value, year_ago),
    }
