import math
from datetime import datetime, timezone
from typing import Optional

from backend.signals.indicators import ATR
from backend.signals.sessions import ET, RTH_CLOSE


def atr_from_bars(bars: list[dict], period: int) -> Optional[float]:
    atr, value = ATR(period), None
    for bar in bars:
        value = atr.update(bar["high"], bar["low"], bar["close"])
    return value


def aggregate(bars: list[dict], minutes: int) -> list[dict]:
    if minutes <= 1:
        return bars
    out: list[dict] = []
    for bar in bars:
        start = bar["time"] - bar["time"] % (minutes * 60)
        if out and out[-1]["time"] == start:
            last = out[-1]
            last.update(high=max(last["high"], bar["high"]), low=min(last["low"], bar["low"]), close=bar["close"])
            last["volume"] += bar["volume"]
        else:
            out.append({**bar, "time": start})
    return out


def completed_days(bars: list[dict], now: datetime) -> list[dict]:
    # Today's bar is partial until the close, and would understate daily ATR.
    local = now.astimezone(ET)
    if bars and datetime.fromtimestamp(bars[-1]["time"], timezone.utc).date() == local.date() and local.time() < RTH_CLOSE:
        return bars[:-1]
    return bars


def risk_amount(mode: str, percent: float, dollars: float, net_liquidation: Optional[float]) -> Optional[float]:
    if mode == "dollars":
        return dollars
    return net_liquidation * percent / 100 if net_liquidation else None


def plan(
    entry: Optional[float],
    atr: Optional[float],
    stop_multiple: float,
    target_multiple: float,
    risk: Optional[float],
    available_funds: Optional[float],
) -> dict:
    if atr is None:
        return {"ok": False, "reason": "No ATR yet for this basis."}
    if risk is None:
        return {"ok": False, "reason": "The account's net liquidation value isn't available, so set a dollar risk instead."}
    if not entry or entry <= 0 or atr <= 0 or stop_multiple <= 0 or target_multiple <= 0 or risk <= 0:
        return {"ok": False, "reason": "Entry, multiples, and risk must all be above zero."}
    stop = round(entry - stop_multiple * atr, 2)
    target = round(entry + target_multiple * atr, 2)
    per_share = entry - stop
    if stop <= 0 or per_share <= 0:
        return {"ok": False, "reason": "The stop would be at or below zero. Lower the stop multiple."}
    # The epsilon keeps 1000 / 0.6 from landing a hair under a whole share.
    shares = math.floor(risk / per_share + 1e-9)
    if shares < 1:
        return {"ok": False, "reason": "The risk amount is smaller than one share's distance to the stop."}
    value = shares * entry
    return {
        "ok": True,
        "entry": entry,
        "stop": stop,
        "target": target,
        "stop_pct": (stop / entry - 1) * 100,
        "target_pct": (target / entry - 1) * 100,
        "shares": shares,
        "position_value": value,
        "risk_dollars": shares * per_share,
        "reward_dollars": shares * (target - entry),
        "reward_risk": (target - entry) / per_share,
        "exceeds_funds": available_funds is not None and value > available_funds,
    }
