import math
from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

from backend.trading.sessions import CLOSED, DAY_SESSIONS, OVERNIGHT

Direction = Literal["long", "short"]
SYMBOLS = ("SOXL", "SOXS")
SMART, OVERNIGHT_VENUE = "SMART", "OVERNIGHT"


@dataclass(frozen=True)
class OrderSpec:
    role: str  # entry | stop | target | exit
    action: str  # BUY | SELL
    order_type: str  # LMT | STP LMT
    quantity: int
    limit_price: float
    stop_price: Optional[float] = None
    exchange: str = SMART
    tif: str = "GTC"
    outside_rth: bool = True
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Plan:
    symbol: str
    direction: Direction
    shares: int
    entry: float
    stop: float
    target: float


@dataclass
class Preview:
    session: str
    orders: list[OrderSpec]
    # Orders the app sends once the entry fills, and the stop it watches overnight.
    after_fill: list[OrderSpec] = field(default_factory=list)
    watched_stop: Optional[float] = None


def _side(direction: Direction) -> tuple[str, str]:
    return ("BUY", "SELL") if direction == "long" else ("SELL", "BUY")


def cents(price: float, direction: str = "nearest") -> float:
    # Round toward the safer side for a capped limit: down for a sell, up for a buy.
    scaled = price * 100
    if direction == "down":
        return math.floor(scaled + 1e-9) / 100
    if direction == "up":
        return math.ceil(scaled - 1e-9) / 100
    return round(scaled) / 100


def capped_limit(price: float, exit_action: str, gap_cap_percent: float) -> float:
    if exit_action == "SELL":
        return cents(price * (1 - gap_cap_percent / 100), "down")
    return cents(price * (1 + gap_cap_percent / 100), "up")


def exits(plan: Plan, gap_cap_percent: float) -> list[OrderSpec]:
    _, exit_action = _side(plan.direction)
    return [
        OrderSpec("stop", exit_action, "STP LMT", plan.shares, capped_limit(plan.stop, exit_action, gap_cap_percent), cents(plan.stop),
                  note="Stop-limit, active outside regular hours"),
        OrderSpec("target", exit_action, "LMT", plan.shares, cents(plan.target), note="Take profit"),
    ]


def overnight_target(plan: Plan) -> OrderSpec:
    _, exit_action = _side(plan.direction)
    return OrderSpec("target", exit_action, "LMT", plan.shares, cents(plan.target), exchange=OVERNIGHT_VENUE, tif="DAY",
                     outside_rth=False, note="Take profit on the overnight venue")


def build(plan: Plan, session: str, gap_cap_percent: float) -> Preview:
    entry_action, _ = _side(plan.direction)
    if session in DAY_SESSIONS:
        entry = OrderSpec("entry", entry_action, "LMT", plan.shares, cents(plan.entry), note="Limit entry")
        return Preview(session, [entry, *exits(plan, gap_cap_percent)])
    if session == OVERNIGHT:
        entry = OrderSpec("entry", entry_action, "LMT", plan.shares, cents(plan.entry), exchange=OVERNIGHT_VENUE, tif="DAY",
                          outside_rth=False, note="Limit entry on the overnight venue")
        # IBKR rejects stop orders overnight (387), so the app watches the stop itself.
        return Preview(session, [entry], after_fill=[*exits(plan, gap_cap_percent), overnight_target(plan)], watched_stop=cents(plan.stop))
    raise ValueError("The market is closed")


def problems(plan: Plan, session: str, mode: Optional[str], live_enabled: bool, max_order_value: float) -> list[str]:
    out = []
    if plan.symbol not in SYMBOLS:
        out.append("Only SOXL and SOXS can be traded here.")
    if plan.shares < 1 or int(plan.shares) != plan.shares:
        out.append("Shares must be a whole number above zero.")
    if min(plan.entry, plan.stop, plan.target) <= 0:
        out.append("Prices must be above zero.")
    if plan.direction == "long":
        if plan.stop >= plan.entry:
            out.append("For a long trade the stop must be below the entry.")
        if plan.target <= plan.entry:
            out.append("For a long trade the take profit must be above the entry.")
    else:
        if plan.stop <= plan.entry:
            out.append("For a short trade the stop must be above the entry.")
        if plan.target >= plan.entry:
            out.append("For a short trade the take profit must be below the entry.")
    value = plan.shares * plan.entry
    if value > max_order_value:
        out.append(f"The order's value, ${value:,.2f}, is above the per-order cap of ${max_order_value:,.2f} in Settings.")
    if mode is None:
        out.append("Not connected to IBKR.")
    elif mode == "live" and not live_enabled:
        out.append("Live trading is off. Switch it on in Settings to place live orders.")
    if session == CLOSED:
        out.append("The market is closed, including the overnight session.")
    return out
