# Proposal

## Why

The user wants to place trades from DeltaAdvisor instead of copying the Trade Planner's numbers into TWS. That includes setting the entry, stop loss, and take profit by dragging lines on a chart, as in IBKR, and trading in the after-hours and overnight sessions, where IBKR's normal stop orders don't work. On Nov 8, 2026 the user chose to lift the app's "never places orders" rule, for paper and live, with a confirmation before every order.

A paper test that day on SOXL found:
- **Pre-market and after-hours (SMART):** a plain stop is accepted, but IBKR ignores "outside regular hours" on it (warning 2109), so it only triggers 9:30–16:00. A stop-limit with outside-RTH and a limit are accepted, with no warning.
- **Overnight (IBKR's OVERNIGHT venue):** stop and stop-limit are rejected ("Unsupported order type", error 387), and only limit orders are allowed.
- **No resting downside limit:** a sell limit below the market fills immediately, so it can't act as a stop.

## What Changes

- **BREAKING (safety model):** the app can place, modify, and cancel orders. The existing connection stays read-only, and orders go through a separate trading session that opens only to place or change orders.
- **Order entry on a chart**, in the Trade Planner view, for SOXL and SOXS, long or short:
  - A candle chart has draggable **entry**, **stop loss**, and **take profit** lines. They start from the planner's ATR values, and dragging updates the size from the planner's risk.
  - **Review** shows the exact orders for the current session, IBKR's commission and margin preview, and the account (PAPER or LIVE). Nothing is sent without **Confirm**.
  - After placement, the working stop and target show on the chart. Dragging one, or cancelling the bracket, also needs a confirmation.
- **Session-aware protection, chosen by the app:**
  - **4:00–20:00 ET (pre-market, regular, after-hours):** a native IBKR bracket, with a limit entry plus a stop-limit and a take-profit limit, outside-RTH on and linked so one cancels the other.
  - **20:00–3:50 ET (overnight):** a limit take profit rests on the overnight venue, and the stop is watched by the app. When the stop is crossed, the app sends a limit a set percentage past the bid or ask (1% by default), cancels the take profit, and alerts if nothing fills within a minute. The app says clearly that this stop only works while it's running and connected.
- **Live trading is off until switched on** in Settings. Live orders show a distinct confirmation, a per-order value cap applies to both accounts, and TWS's own order precautions stay on.
- The "never places orders" rule in the specs, `CLAUDE.md`, and `tests/test_orders.py` is replaced by narrower guards: one backend module may send orders, and only with a confirmation from the user that hasn't expired.

## Capabilities

### New Capabilities

- `order-entry`: placing, modifying, and cancelling SOXL and SOXS bracket orders from a chart, session-aware protection including the app-watched overnight stop, and the confirmation and limit safeguards.

### Modified Capabilities

- `ibkr-connection`: the read-only requirement becomes a read-only main connection, plus a separate trading session used only by order entry after confirmation.
- `trade-planner`: the planner still doesn't place orders itself, but hands its plan to order entry on the same view.

## Impact

- **IBKR access:**
  - Adds an order-capable API session, on a separate client ID, to the same TWS the app is connected to. It opens only when the user places, changes, or cancels an order, or while an app-watched stop is active.
  - Live orders need TWS's Read-Only API turned off on the live account, which the app explains. Paper already has it off.
- **Order handling:**
  - New. Orders come only from the order entry panel, after a confirmation tied to the exact preview. They're capped by a per-order value limit, and blocked on live unless live trading is switched on.
  - The Orders view stays read-only.
- **API keys:** not touched.
- **Data leaving the machine:** orders go to IBKR through the local TWS only. Nothing goes to AI providers.
- **Code:** new `backend/trading/` (sessions, order building, the trading session, the overnight stop watcher, persistence), a router, SQLite tables for brackets and watched stops, `backend/main.py`, the Trade Planner page and a new chart component, settings, types, the API client, README, `CLAUDE.md`, `tests/test_orders.py`, and new tests.
