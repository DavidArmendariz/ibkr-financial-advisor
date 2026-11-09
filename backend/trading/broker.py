import asyncio
import json
import logging
import math
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from ib_async import IB, LimitOrder, Order, Stock, StopLimitOrder
from sqlmodel import select

from backend import database
from backend.database import TradeBracket, WatchedStop
from backend.trading.config import get_trading_settings
from backend.trading.orders import OVERNIGHT_VENUE, SMART, OrderSpec, Plan, Preview, build, capped_limit, cents, exits, overnight_target, problems
from backend.trading.session import TradingSession, TradingSessionError
from backend.trading.sessions import OVERNIGHT, session_at

log = logging.getLogger(__name__)

# This is the only module in the backend allowed to send, change, or cancel orders
# (tests/test_orders.py enforces it), and it only does so for a confirmed review.
REVIEW_SECONDS = 120
REF_PREFIX = "deltaadvisor"
EXIT_FILL_SECONDS = 60
QUALIFY_TIMEOUT = 15
WHAT_IF_TIMEOUT = 15
ACTIVE_STATUSES = {"PendingSubmit", "ApiPending", "PreSubmitted", "Submitted"}
DONE_STATUSES = {"Filled", "Cancelled", "ApiCancelled", "Inactive"}
INFO_CODES = {399, 2104, 2106, 2107, 2108, 2109, 2119, 2158}
# IBKR reports a one-cancels-all cancellation as 202 with no reason: not a rejection.
OCA_CANCEL = 202
RECONCILE_AFTER = 5
# TWS cancels orders routed straight to the overnight venue while this precaution is on.
DIRECTED_ORDER_PRECAUTION = 10329
EXPLAIN = {
    DIRECTED_ORDER_PRECAUTION: (
        "TWS cancelled the order because it was routed straight to the overnight venue, which overnight orders must be. In TWS, "
        "Global Configuration > API > Precautions, tick \"Bypass Redirect Order warning for Stock API Orders\"."
    ),
}
UNSET = 1e300


class TradingError(Exception):
    def __init__(self, status: int, message: str, problems: Optional[list[str]] = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.problems = problems or [message]


@dataclass
class Pending:
    kind: str  # place | modify | cancel
    mode: str
    account: str
    port: int
    expires: datetime
    plan: Optional[Plan] = None
    preview: Optional[Preview] = None
    bracket_id: Optional[str] = None
    role: Optional[str] = None
    price: Optional[float] = None


@dataclass
class Live:
    # In-memory view of a bracket's orders in the trading session, keyed by role.
    trades: dict[str, Any] = field(default_factory=dict)


def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    return None if dt is None else (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))


def _number(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and abs(v) < UNSET else None


def ref(bracket_id: str, role: str) -> str:
    return f"{REF_PREFIX}:{bracket_id}:{role}"


def parse_ref(order_ref: str) -> Optional[tuple[str, str]]:
    parts = (order_ref or "").split(":")
    return (parts[1], parts[2]) if len(parts) == 3 and parts[0] == REF_PREFIX else None


def make_order(spec: OrderSpec, account: str, order_ref: str) -> Order:
    if spec.order_type == "STP LMT":
        order = StopLimitOrder(spec.action, spec.quantity, spec.limit_price, spec.stop_price)
    elif spec.order_type == "LMT":
        order = LimitOrder(spec.action, spec.quantity, spec.limit_price)
    else:
        raise ValueError(f"Unsupported order type {spec.order_type}")
    order.tif = spec.tif
    order.outsideRth = spec.outside_rth
    order.account = account
    order.orderRef = order_ref
    return order


class Broker:
    def __init__(self, session: TradingSession, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.session = session
        self.clock = clock
        self.pending: dict[str, Pending] = {}
        self.notify: Callable[[str, str], None] = lambda title, body: None
        self._contracts: dict[tuple[str, str], Any] = {}
        self._live: dict[str, Live] = {}
        self._errors: dict[int, tuple[int, str]] = {}
        self._cancelling: set[int] = set()
        self._exit_checks: dict[str, asyncio.Task] = {}
        session.on_connect.append(self._wire)

    # ── Reviews ──────────────────────────────────────────────────────────────

    def _identity(self) -> tuple[Optional[int], Optional[str], Optional[str]]:
        try:
            return self.session.main_identity()
        except TradingSessionError:
            return None, None, None

    async def review(self, plan: Plan) -> dict:
        now = self.clock()
        settings = get_trading_settings()
        port, mode, account = self._identity()
        session = session_at(now)
        issues = problems(plan, session, mode, settings.live_enabled, settings.max_order_value)
        if issues:
            raise TradingError(422, issues[0], issues)
        preview = build(plan, session, settings.gap_cap_percent)
        ib = await self._ensure()
        entry = preview.orders[0]
        contract = await self._contract(ib, plan.symbol, entry.exchange)
        what_if = await self._what_if(ib, contract, entry, account)
        token = secrets.token_urlsafe(24)
        self.pending[token] = Pending("place", mode, account, port, now + timedelta(seconds=REVIEW_SECONDS), plan=plan, preview=preview)
        return {
            "token": token,
            "expires_at": (now + timedelta(seconds=REVIEW_SECONDS)).isoformat(),
            "kind": "place",
            "mode": mode,
            "account": account,
            "session": session,
            "plan": plan.__dict__,
            "orders": [o.to_dict() for o in preview.orders],
            "after_fill": [o.to_dict() for o in preview.after_fill],
            "watched_stop": preview.watched_stop,
            "risk": round(abs(plan.entry - plan.stop) * plan.shares, 2),
            "reward": round(abs(plan.target - plan.entry) * plan.shares, 2),
            "value": round(plan.entry * plan.shares, 2),
            "what_if": what_if,
            "gap_cap_percent": settings.gap_cap_percent,
        }

    async def review_modify(self, bracket_id: str, role: str, price: float) -> dict:
        if role not in ("stop", "target"):
            raise TradingError(422, "Only the stop and the take profit can be moved.")
        now = self.clock()
        port, mode, account = self._identity()
        bracket = await self._bracket(bracket_id)
        self._check_owner(bracket, mode, account)
        if bracket.state not in ("working", "open"):
            raise TradingError(409, "This bracket isn't working any more.")
        price = cents(price)
        long = bracket.direction == "long"
        if role == "stop" and ((long and price >= bracket.entry) or (not long and price <= bracket.entry)):
            raise TradingError(422, f"For a {bracket.direction} trade the stop must be {'below' if long else 'above'} the entry.")
        if role == "target" and ((long and price <= bracket.entry) or (not long and price >= bracket.entry)):
            raise TradingError(422, f"For a {bracket.direction} trade the take profit must be {'above' if long else 'below'} the entry.")
        token = secrets.token_urlsafe(24)
        self.pending[token] = Pending("modify", mode, account, port, now + timedelta(seconds=REVIEW_SECONDS), bracket_id=bracket_id, role=role, price=price)
        old = bracket.stop if role == "stop" else bracket.target
        return {"token": token, "expires_at": (now + timedelta(seconds=REVIEW_SECONDS)).isoformat(), "kind": "modify", "mode": mode,
                "account": account, "bracket_id": bracket_id, "role": role, "from": old, "to": price}

    async def review_cancel(self, bracket_id: str) -> dict:
        now = self.clock()
        port, mode, account = self._identity()
        bracket = await self._bracket(bracket_id)
        self._check_owner(bracket, mode, account)
        if bracket.state not in ("working", "open"):
            raise TradingError(409, "This bracket isn't working any more.")
        token = secrets.token_urlsafe(24)
        self.pending[token] = Pending("cancel", mode, account, port, now + timedelta(seconds=REVIEW_SECONDS), bracket_id=bracket_id)
        warning = (
            f"The entry has filled, so cancelling leaves {bracket.shares} {bracket.symbol} shares open with no stop or take profit."
            if bracket.state == "open" else None
        )
        return {"token": token, "expires_at": (now + timedelta(seconds=REVIEW_SECONDS)).isoformat(), "kind": "cancel", "mode": mode,
                "account": account, "bracket_id": bracket_id, "warning": warning}

    @staticmethod
    def _check_owner(bracket: TradeBracket, mode: Optional[str], account: Optional[str]) -> None:
        if mode is None:
            raise TradingError(503, "Not connected to IBKR.")
        if bracket.mode != mode or bracket.account != account:
            raise TradingError(409, f"This bracket belongs to the {bracket.mode} account. Connect to it to change the bracket.")

    # ── Confirmation ─────────────────────────────────────────────────────────

    async def confirm(self, token: str) -> dict:
        pending = self.pending.pop(token, None)
        now = self.clock()
        if pending is None:
            raise TradingError(409, "This review was already used or doesn't exist. Review again.")
        if now > pending.expires:
            raise TradingError(409, "This review expired after 2 minutes. Review again.")
        port, mode, account = self._identity()
        if (port, mode, account) != (pending.port, pending.mode, pending.account):
            raise TradingError(409, "The connected account changed since the review. Review again.")
        settings = get_trading_settings()
        if mode == "live" and not settings.live_enabled:
            raise TradingError(422, "Live trading is off. Switch it on in Settings to place live orders.")
        if pending.kind == "place":
            if session_at(now) != pending.preview.session:
                raise TradingError(409, "The trading session changed since the review. Review again.")
            issues = problems(pending.plan, pending.preview.session, mode, settings.live_enabled, settings.max_order_value)
            if issues:
                raise TradingError(422, issues[0], issues)
            return await self._place(pending, now)
        if pending.kind == "modify":
            return await self._modify(pending.bracket_id, pending.role, pending.price)
        return await self._cancel(pending.bracket_id)

    # ── Sending ──────────────────────────────────────────────────────────────

    async def _ensure(self) -> IB:
        try:
            return await self.session.ensure()
        except TradingSessionError as e:
            raise TradingError(503, str(e))

    async def _contract(self, ib: IB, symbol: str, exchange: str) -> Any:
        key = (symbol, exchange)
        if key not in self._contracts:
            contract = Stock(symbol, exchange, "USD")
            qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), QUALIFY_TIMEOUT)
            if not qualified or not getattr(qualified[0], "conId", 0):
                raise TradingError(502, f"IBKR doesn't list {symbol} on {exchange}.")
            self._contracts[key] = qualified[0]
        return self._contracts[key]

    async def _what_if(self, ib: IB, contract: Any, spec: OrderSpec, account: str) -> dict:
        try:
            state = await asyncio.wait_for(ib.whatIfOrderAsync(contract, make_order(spec, account, "")), WHAT_IF_TIMEOUT)
        except Exception as e:
            return {"available": False, "note": f"IBKR's preview wasn't available ({type(e).__name__})."}
        if state is None:
            return {"available": False, "note": "IBKR's preview wasn't available."}
        return {
            "available": True,
            "commission": _number(getattr(state, "commission", None)),
            "min_commission": _number(getattr(state, "minCommission", None)),
            "max_commission": _number(getattr(state, "maxCommission", None)),
            "init_margin_change": _number(getattr(state, "initMarginChange", None)),
            "warning": getattr(state, "warningText", "") or None,
        }

    def _send(self, ib: IB, contract: Any, spec: OrderSpec, account: str, bracket_id: str, role: str, **extra: Any) -> Any:
        order = make_order(spec, account, ref(bracket_id, role))
        for key, value in extra.items():
            setattr(order, key, value)
        trade = ib.placeOrder(contract, order)
        self._live.setdefault(bracket_id, Live()).trades[role] = trade
        return trade

    async def _place(self, pending: Pending, now: datetime) -> dict:
        plan, preview = pending.plan, pending.preview
        ib = await self._ensure()
        bracket_id = uuid.uuid4().hex[:12]
        oca = f"DA-{bracket_id}"
        entry_spec = preview.orders[0]
        contract = await self._contract(ib, plan.symbol, entry_spec.exchange)
        orders: dict[str, dict] = {}
        if preview.session == OVERNIGHT:
            trade = self._send(ib, contract, entry_spec, pending.account, bracket_id, "entry")
            orders["entry"] = self._order_info(trade, entry_spec)
        else:
            # A native bracket: the children only go live once the parent fills, and
            # transmitting the last child sends all three together.
            parent = self._send(ib, contract, entry_spec, pending.account, bracket_id, "entry", transmit=False)
            stop_spec, target_spec = preview.orders[1], preview.orders[2]
            stop = self._send(ib, contract, stop_spec, pending.account, bracket_id, "stop",
                              parentId=parent.order.orderId, ocaGroup=oca, ocaType=1, transmit=False)
            target = self._send(ib, contract, target_spec, pending.account, bracket_id, "target",
                                parentId=parent.order.orderId, ocaGroup=oca, ocaType=1, transmit=True)
            orders = {"entry": self._order_info(parent, entry_spec), "stop": self._order_info(stop, stop_spec), "target": self._order_info(target, target_spec)}
        row = TradeBracket(
            id=bracket_id, created_at=now, mode=pending.mode, account=pending.account, symbol=plan.symbol, direction=plan.direction,
            shares=plan.shares, entry=cents(plan.entry), stop=cents(plan.stop), target=cents(plan.target), session=preview.session,
            state="working", orders=json.dumps(orders), updated_at=now,
        )
        async with database.AsyncSessionLocal() as s:
            s.add(row)
            await s.commit()
        return await self.bracket_record(bracket_id)

    @staticmethod
    def _order_info(trade: Any, spec: OrderSpec) -> dict:
        return {"order_id": trade.order.orderId, "perm_id": trade.order.permId or None, "status": trade.orderStatus.status or "PendingSubmit",
                "type": spec.order_type, "action": spec.action, "price": spec.stop_price if spec.order_type == "STP LMT" else spec.limit_price,
                "limit": spec.limit_price, "exchange": spec.exchange, "message": None}

    def _trade(self, bracket_id: str, role: str, order_id: Optional[int]) -> Optional[Any]:
        live = self._live.get(bracket_id)
        if live and role in live.trades:
            return live.trades[role]
        ib = self.session.ib
        if ib is None or order_id is None:
            return None
        return next((t for t in ib.trades() if t.order.orderId == order_id), None)

    async def _modify(self, bracket_id: str, role: str, price: float) -> dict:
        ib = await self._ensure()
        settings = get_trading_settings()
        bracket = await self._bracket(bracket_id)
        orders = json.loads(bracket.orders)
        roles = ["stop"] if role == "stop" else [r for r in ("target", "target_overnight") if r in orders]
        for r in roles:
            info = orders.get(r)
            trade = self._trade(bracket_id, r, info and info["order_id"])
            if trade is None or trade.orderStatus.status in DONE_STATUSES:
                continue
            if r == "stop":
                trade.order.auxPrice = price
                trade.order.lmtPrice = capped_limit(price, trade.order.action, settings.gap_cap_percent)
            else:
                trade.order.lmtPrice = price
            ib.placeOrder(trade.contract, trade.order)
            info.update(price=price, limit=trade.order.lmtPrice)
        async with database.AsyncSessionLocal() as s:
            row = await s.get(TradeBracket, bracket_id)
            setattr(row, role, price)
            row.orders = json.dumps(orders)
            row.updated_at = self.clock()
            s.add(row)
            if role == "stop":
                watched = await s.get(WatchedStop, bracket_id)
                if watched is not None:
                    watched.level = price
                    s.add(watched)
            await s.commit()
        return await self.bracket_record(bracket_id)

    async def _cancel(self, bracket_id: str) -> dict:
        ib = await self._ensure()
        bracket = await self._bracket(bracket_id)
        for role, info in json.loads(bracket.orders).items():
            trade = self._trade(bracket_id, role, info.get("order_id"))
            if trade is not None and trade.orderStatus.status not in DONE_STATUSES:
                self._cancelling.add(trade.order.orderId)
                ib.cancelOrder(trade.order)
        async with database.AsyncSessionLocal() as s:
            row = await s.get(TradeBracket, bracket_id)
            row.state = "cancelled"
            row.updated_at = self.clock()
            s.add(row)
            watched = await s.get(WatchedStop, bracket_id)
            if watched is not None:
                watched.active = False
                s.add(watched)
            await s.commit()
        return await self.bracket_record(bracket_id)

    # ── Overnight protection (part of a confirmed bracket) ──────────────────

    async def place_after_fill(self, bracket_id: str) -> None:
        # After an overnight entry fills: stop and take profit ready for 4:00 at IBKR,
        # a take profit on the overnight venue, and the stop the app watches tonight.
        bracket = await self._bracket(bracket_id)
        plan = Plan(bracket.symbol, bracket.direction, bracket.shares, bracket.entry, bracket.stop, bracket.target)
        settings = get_trading_settings()
        ib = await self._ensure()
        oca = f"DA-{bracket_id}"
        orders = json.loads(bracket.orders)
        smart = await self._contract(ib, bracket.symbol, SMART)
        for spec in exits(plan, settings.gap_cap_percent):
            if spec.role not in orders:
                trade = self._send(ib, smart, spec, bracket.account, bracket_id, spec.role, ocaGroup=oca, ocaType=1)
                orders[spec.role] = self._order_info(trade, spec)
        await self._save_orders(bracket_id, orders)
        await self.protect_overnight(bracket_id)

    async def protect_overnight(self, bracket_id: str) -> None:
        bracket = await self._bracket(bracket_id)
        if bracket.state != "open":
            return
        orders = json.loads(bracket.orders)
        current = orders.get("target_overnight")
        trade = current and self._trade(bracket_id, "target_overnight", current["order_id"])
        if trade is None or trade.orderStatus.status in DONE_STATUSES:
            ib = await self._ensure()
            plan = Plan(bracket.symbol, bracket.direction, bracket.shares, bracket.entry, bracket.stop, bracket.target)
            spec = overnight_target(plan)
            contract = await self._contract(ib, bracket.symbol, OVERNIGHT_VENUE)
            trade = self._send(ib, contract, spec, bracket.account, bracket_id, "target_overnight", ocaGroup=f"DA-{bracket_id}", ocaType=1)
            orders["target_overnight"] = self._order_info(trade, spec)
            await self._save_orders(bracket_id, orders)
        exit_action = "SELL" if bracket.direction == "long" else "BUY"
        async with database.AsyncSessionLocal() as s:
            watched = await s.get(WatchedStop, bracket_id)
            if watched is None:
                s.add(WatchedStop(bracket_id=bracket_id, level=bracket.stop, exit_action=exit_action, gap_cap_percent=get_trading_settings().gap_cap_percent))
            elif not watched.active and watched.triggered_at is None:
                watched.active = True
                s.add(watched)
            await s.commit()

    async def trigger_stop(self, bracket_id: str, bid: Optional[float], ask: Optional[float]) -> None:
        bracket = await self._bracket(bracket_id)
        ib = await self._ensure()
        orders = json.loads(bracket.orders)
        info = orders.get("target_overnight")
        target = info and self._trade(bracket_id, "target_overnight", info["order_id"])
        if target is not None and target.orderStatus.status not in DONE_STATUSES:
            self._cancelling.add(target.order.orderId)
            ib.cancelOrder(target.order)
        async with database.AsyncSessionLocal() as s:
            watched = await s.get(WatchedStop, bracket_id)
        reference = bid if watched.exit_action == "SELL" else ask
        price = capped_limit(reference, watched.exit_action, watched.gap_cap_percent)
        spec = OrderSpec("exit", watched.exit_action, "LMT", bracket.shares, price, exchange=OVERNIGHT_VENUE, tif="DAY", outside_rth=False,
                         note="Exit from the app-watched stop")
        contract = await self._contract(ib, bracket.symbol, OVERNIGHT_VENUE)
        trade = self._send(ib, contract, spec, bracket.account, bracket_id, "exit", ocaGroup=f"DA-{bracket_id}", ocaType=1)
        orders["exit"] = self._order_info(trade, spec)
        await self._save_orders(bracket_id, orders)
        async with database.AsyncSessionLocal() as s:
            watched = await s.get(WatchedStop, bracket_id)
            watched.triggered_at = self.clock()
            watched.exit_order_id = trade.order.orderId
            watched.active = False
            s.add(watched)
            await s.commit()
        self.notify(
            f"{bracket.symbol} stop hit overnight",
            f"{'Bid' if watched.exit_action == 'SELL' else 'Ask'} {reference:.2f} crossed the stop at {watched.level:.2f}. "
            f"Sent a {watched.exit_action.lower()} limit at {price:.2f} for {bracket.shares} shares and cancelled the take profit.",
        )
        self._exit_checks[bracket_id] = asyncio.create_task(self._check_exit_filled(bracket_id, trade))

    async def _check_exit_filled(self, bracket_id: str, trade: Any) -> None:
        await asyncio.sleep(EXIT_FILL_SECONDS)
        if trade.orderStatus.status != "Filled":
            bracket = await self._bracket(bracket_id)
            self.notify(
                f"{bracket.symbol} stop exit not filled",
                f"The exit limit at {trade.order.lmtPrice:.2f} hasn't filled after a minute ({trade.orderStatus.status}). Check the position in TWS.",
            )

    # ── Order events ─────────────────────────────────────────────────────────

    def _wire(self, ib: IB) -> None:
        ib.orderStatusEvent += self._on_status
        ib.errorEvent += self._on_error
        for trade in ib.trades():
            self._on_status(trade)

    def _on_error(self, req_id: int, code: int, message: str, contract: Any) -> None:
        if code not in INFO_CODES:
            self._errors[req_id] = (code, message)

    def _on_status(self, trade: Any) -> None:
        parsed = parse_ref(trade.order.orderRef)
        if parsed is None:
            return
        bracket_id, role = parsed
        self._live.setdefault(bracket_id, Live()).trades[role] = trade
        try:
            asyncio.get_running_loop().create_task(self.apply_status(bracket_id, role, trade))
        except RuntimeError:
            pass

    async def apply_status(self, bracket_id: str, role: str, trade: Any) -> None:
        status = trade.orderStatus.status
        order_id = trade.order.orderId
        async with database.AsyncSessionLocal() as s:
            row = await s.get(TradeBracket, bracket_id)
            if row is None:
                return
            orders = json.loads(row.orders)
            info = orders.setdefault(role, {"order_id": order_id})
            info["status"] = status
            info["perm_id"] = trade.order.permId or info.get("perm_id")
            error = self._errors.get(order_id)
            if error:
                info["message"] = EXPLAIN.get(error[0]) or f"IBKR {error[0]}: {error[1]}"
            row.orders = json.dumps(orders)
            row.updated_at = self.clock()
            event = None
            if role == "entry" and status == "Filled" and row.state == "working":
                row.state = "open"
                event = "filled"
            elif role == "entry" and status in ("Cancelled", "ApiCancelled", "Inactive") and row.state == "working" and order_id not in self._cancelling:
                row.state = "rejected"
                row.warning = info.get("message") or "IBKR cancelled the entry."
                event = "rejected"
            elif role in ("stop", "target", "target_overnight", "exit") and status == "Filled" and row.state == "open":
                row.state = "closed"
                event = "closed"
            elif (
                role in ("stop", "target") and status in ("Cancelled", "ApiCancelled", "Inactive") and row.state == "open"
                and order_id not in self._cancelling and error is not None and error[0] != OCA_CANCEL
            ):
                name = "stop" if role == "stop" else "take profit"
                row.warning = f"The position has no {name}: {info['message']}"
                event = "unprotected"
            s.add(row)
            if event == "closed":
                watched = await s.get(WatchedStop, bracket_id)
                if watched is not None:
                    watched.active = False
                    s.add(watched)
            await s.commit()
        if event == "filled":
            self.notify(f"{row.symbol} entry filled", f"{row.direction.title()} {row.shares} at {trade.orderStatus.avgFillPrice or row.entry:.2f}.")
            if row.session == OVERNIGHT or session_at(self.clock()) == OVERNIGHT:
                await self.place_after_fill(bracket_id)
        elif event == "closed":
            self.notify(f"{row.symbol} bracket closed", f"The {role.replace('_', ' ')} filled at {trade.orderStatus.avgFillPrice or 0:.2f}.")
            asyncio.get_running_loop().create_task(self._reconcile_later(bracket_id))
        elif event in ("unprotected", "rejected"):
            self.notify(f"{row.symbol} order problem", row.warning or "")

    async def _reconcile_later(self, bracket_id: str) -> None:
        await asyncio.sleep(RECONCILE_AFTER)
        await self.reconcile(bracket_id)

    async def reconcile(self, bracket_id: str) -> None:
        # TWS doesn't always report the final status of orders a one-cancels-all group
        # cancelled, so an exit still marked working but no longer open at IBKR was cancelled.
        ib = self.session.ib
        if ib is None or not ib.isConnected():
            return
        try:
            open_ids = {t.order.orderId for t in await asyncio.wait_for(ib.reqOpenOrdersAsync(), QUALIFY_TIMEOUT)}
        except Exception:
            return
        bracket = await self._bracket(bracket_id)
        orders = json.loads(bracket.orders)
        changed = False
        for info in orders.values():
            if info.get("status") in ACTIVE_STATUSES | {"PendingCancel"} and info.get("order_id") not in open_ids:
                info["status"] = "Cancelled"
                changed = True
        if changed:
            await self._save_orders(bracket_id, orders)

    async def _save_orders(self, bracket_id: str, orders: dict) -> None:
        async with database.AsyncSessionLocal() as s:
            row = await s.get(TradeBracket, bracket_id)
            row.orders = json.dumps(orders)
            row.updated_at = self.clock()
            s.add(row)
            await s.commit()

    # ── Records ──────────────────────────────────────────────────────────────

    async def _bracket(self, bracket_id: str) -> TradeBracket:
        async with database.AsyncSessionLocal() as s:
            row = await s.get(TradeBracket, bracket_id)
        if row is None:
            raise TradingError(404, "Bracket not found.")
        return row

    async def bracket_record(self, bracket_id: str) -> dict:
        async with database.AsyncSessionLocal() as s:
            row = await s.get(TradeBracket, bracket_id)
            watched = await s.get(WatchedStop, bracket_id)
        return self._record(row, watched)

    @staticmethod
    def _record(row: TradeBracket, watched: Optional[WatchedStop]) -> dict:
        return {
            "id": row.id, "created_at": _utc(row.created_at).isoformat(), "updated_at": _utc(row.updated_at).isoformat(),
            "mode": row.mode, "account": row.account, "symbol": row.symbol, "direction": row.direction, "shares": row.shares,
            "entry": row.entry, "stop": row.stop, "target": row.target, "session": row.session, "state": row.state,
            "orders": json.loads(row.orders), "warning": row.warning,
            "watched_stop": None if watched is None else {
                "level": watched.level, "active": watched.active, "exit_action": watched.exit_action,
                "triggered_at": _utc(watched.triggered_at).isoformat() if watched.triggered_at else None,
                "gaps": json.loads(watched.gaps),
            },
        }

    async def brackets(self, mode: Optional[str], limit: int = 20) -> list[dict]:
        query = select(TradeBracket).order_by(TradeBracket.created_at.desc()).limit(limit)
        if mode is not None:
            query = query.where(TradeBracket.mode == mode)
        async with database.AsyncSessionLocal() as s:
            rows = (await s.exec(query)).all()
            watched = {w.bracket_id: w for w in (await s.exec(select(WatchedStop))).all()}
        return [self._record(r, watched.get(r.id)) for r in rows]
