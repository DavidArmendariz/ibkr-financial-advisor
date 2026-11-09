import re
import statistics
from dataclasses import dataclass
from typing import Optional

CHEAPER_BY = 0.20
MIN_PEERS = 3
MIN_YEARS = 3
HISTORY_YEARS = 5
MAX_PEERS = 10
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")


@dataclass(frozen=True)
class Multiple:
    key: str
    label: str
    fields: tuple[str, ...]  # Finnhub metric fields, first available wins
    series: Optional[str]  # Finnhub yearly series, when there is one
    # Finnhub leaves the multiple empty when this is negative, as P/E is on losses.
    loss_field: Optional[str] = None


MULTIPLES = (
    Multiple("pe", "P/E", ("peTTM", "peBasicExclExtraTTM"), "pe", "epsTTM"),
    Multiple("ps", "P/S", ("psTTM",), "ps"),
    Multiple("ev_ebitda", "EV/EBITDA", ("evEbitdaTTM",), "evEbitda"),
    Multiple("ev_fcf", "EV/FCF", ("currentEv/freeCashFlowTTM",), None),
    Multiple("pb", "P/B", ("pbQuarterly", "pbAnnual"), "pb"),
)

QUALITY = (
    ("revenue_growth", "Revenue growth (TTM, YoY)", ("revenueGrowthTTMYoy",), "%"),
    ("eps_growth", "EPS growth (TTM, YoY)", ("epsGrowthTTMYoy",), "%"),
    ("net_margin", "Net margin (TTM)", ("netProfitMarginTTM",), "%"),
    ("operating_margin", "Operating margin (TTM)", ("operatingMarginTTM",), "%"),
    ("roe", "Return on equity (TTM)", ("roeTTM",), "%"),
    ("debt_to_equity", "Debt to equity", ("totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"), "x"),
)


def clean_ticker(raw: str) -> Optional[str]:
    ticker = raw.strip().upper()
    return ticker if TICKER.match(ticker) else None


def first(metric: dict, fields: tuple[str, ...]) -> Optional[float]:
    for f in fields:
        v = metric.get(f)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def clean_peers(ticker: str, peers: list) -> list[str]:
    # Finnhub lists the stock itself among its peers, and can repeat a peer.
    out = [p.upper() for p in dict.fromkeys(p for p in peers if isinstance(p, str)) if p.upper() != ticker]
    return list(dict.fromkeys(out))[:MAX_PEERS]


def meaningful(value: Optional[float]) -> bool:
    # A multiple on losses, negative EBITDA, or negative cash flow isn't comparable.
    return value is not None and value > 0


def peer_median(values: list[Optional[float]]) -> Optional[float]:
    usable = [v for v in values if meaningful(v)]
    return statistics.median(usable) if len(usable) >= MIN_PEERS else None


def history_median(series: list[dict], years: int = HISTORY_YEARS) -> tuple[Optional[float], int]:
    newest = sorted((p for p in series if isinstance(p.get("v"), (int, float))), key=lambda p: p["period"], reverse=True)[:years]
    usable = [float(p["v"]) for p in newest if p["v"] > 0]
    return (statistics.median(usable) if len(usable) >= MIN_YEARS else None), len(usable)


def cheaper(value: Optional[float], median: Optional[float]) -> Optional[bool]:
    if not meaningful(value) or median is None:
        return None
    return value <= median * (1 - CHEAPER_BY)


def compare(metric: dict, series: dict, peer_metrics: list[dict]) -> list[dict]:
    rows = []
    for m in MULTIPLES:
        value = first(metric, m.fields)
        loss = m.loss_field is not None and (first(metric, (m.loss_field,)) or 0) < 0
        peers = [first(p, m.fields) for p in peer_metrics]
        p_median = peer_median(peers)
        h_median, h_years = history_median(series.get(m.series, [])) if m.series else (None, 0)
        rows.append(
            {
                "key": m.key,
                "label": m.label,
                "value": value if meaningful(value) else None,
                "status": "ok" if meaningful(value) else ("missing" if value is None and not loss else "not_meaningful"),
                "peer_median": p_median,
                "peer_count": sum(1 for v in peers if meaningful(v)),
                "cheaper_than_peers": cheaper(value, p_median),
                "has_history": m.series is not None,
                "history_median": h_median,
                "history_years": h_years,
                "cheaper_than_history": cheaper(value, h_median),
            }
        )
    return rows


def quality(metric: dict) -> list[dict]:
    return [{"key": k, "label": label, "value": first(metric, fields), "unit": unit} for k, label, fields, unit in QUALITY]


def ratings(rows: list[dict]) -> Optional[dict]:
    def counts(r: dict) -> dict:
        c = {k: int(r.get(k) or 0) for k in ("strongBuy", "buy", "hold", "sell", "strongSell")}
        total = sum(c.values())
        return {
            "period": r.get("period"),
            "strong_buy": c["strongBuy"],
            "buy": c["buy"],
            "hold": c["hold"],
            "sell": c["sell"],
            "strong_sell": c["strongSell"],
            "total": total,
            "buy_share": (c["strongBuy"] + c["buy"]) / total if total else None,
        }

    ordered = sorted((r for r in rows if r.get("period")), key=lambda r: r["period"], reverse=True)
    if not ordered:
        return None
    return {"latest": counts(ordered[0]), "previous": counts(ordered[1]) if len(ordered) > 1 else None}
