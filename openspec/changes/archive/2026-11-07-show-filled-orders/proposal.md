# Proposal

## Why

An order leaves the Orders view as soon as it fills, so the user's filled overnight SOXS order seemed to have disappeared. The user wants to see filled orders.

## What Changes

- The Orders view adds a Filled orders section, newest first.
- Fills are saved to the local database, separately for live and paper, so the list becomes a permanent history.
- Each row shows the time, instrument, side, quantity, average price, venue, commission, and realized P&L.
- The page title becomes Orders, and Refresh covers both sections.
- Open orders behave as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `open-orders`: adds the filled orders list.

## Impact

- **IBKR access:** read-only. Adds `reqExecutions`, which works with TWS's Read-Only API on.
- **Order handling:** nothing places, changes, or cancels orders, and `tests/test_orders.py` still guards that.
- **API keys:** not touched.
- **Data leaving the machine:** none. Fills stay in the local SQLite database, with no account number.
- **Code:** `backend/services/ibkr_service.py`, `backend/database.py`, `backend/main.py`, `backend/routers/orders.py`, `src/pages/Orders.tsx`, a new hook and table, types, API client, README, tests.
