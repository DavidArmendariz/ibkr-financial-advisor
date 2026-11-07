# Proposal

## Why

The user wants to see ATR, and to size SOXL or SOXS trades with stops and targets based on it. ATR measures how far price typically moves per bar or per day. A stop set from ATR scales with volatility instead of being a fixed distance that's too tight on wild days and too loose on calm ones.

The user also asked for the app to place those orders. That conflicts with the project's core rule that the app never places orders, which `tests/test_orders.py` enforces, and with TWS's Read-Only API being off, which leaves the app's code as the only guard. This change plans trades without placing them. Order placement needs the user's explicit decision to drop the rule, and would be its own change.

## What Changes

- Signals computes Wilder's ATR (period 14, configurable) on each bar, shown with the live values.
- A new **Trade Planner** view, below Signal History, shows the price, live bid and ask, intraday ATR, and daily ATR for SOXL and SOXS. The ask is the default entry.
- For a chosen symbol, it calculates a long trade: stop and target from ATR multiples, and shares from the dollars at risk, either fixed or a percent of net liquidation.
- It shows the bracket values to enter in TWS, with a Copy control.
- Nothing places, modifies, or cancels orders.

## Capabilities

### New Capabilities

- `trade-planner`: ATR for SOXL and SOXS, and ATR-based stop, target, and size calculations.

### Modified Capabilities

- `signal-alerts`: adds ATR to the indicators and the Signals view.

## Impact

- **IBKR access:** read-only. Adds historical bar requests for SOXS (1-minute) and both symbols (daily), two real-time quote lines while the planner is open, and the account summary already used by the Dashboard.
- **Order handling:** none. The rule stays, and `tests/test_orders.py` keeps guarding it.
- **API keys:** not touched.
- **Data leaving the machine:** none.
- **Code:** `backend/signals/indicators.py`, `models.py`, `config.py`, a new `backend/planner/` and router, `backend/main.py`, the Signals live values and settings, a new page, hook, and components, the sidebar, types, README, `CLAUDE.md`, tests.
