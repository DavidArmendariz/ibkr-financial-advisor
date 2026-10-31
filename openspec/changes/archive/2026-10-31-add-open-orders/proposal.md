# Proposal

## Why

The app shows positions but not working orders, so checking what is resting in the market (a stop protecting SOXL, a limit waiting to fill) means switching to TWS. A read-only Orders view puts that next to the rest of the account.

## What Changes

- Add an **Orders** item to the sidebar, directly below Dashboard, opening a view of the account's current open orders.
- Each order shows its instrument, side, type, quantity, filled and remaining quantity, limit and stop prices, time in force, and status. The view refreshes while it is open and has a manual refresh.
- Add `GET /api/orders/open`, which reads open orders from TWS / IB Gateway, including orders placed in TWS itself or by other API clients.
- If TWS refuses or never answers the request, which may happen with **Read-Only API** enabled, the view explains that and stops polling, so it cannot raise the TWS write-access pop-up repeatedly.
- Narrow the wording of the read-only requirement: reading open orders is allowed, while placing, modifying, or cancelling orders stays forbidden. The view has no order actions.

## Capabilities

### New Capabilities

- `open-orders`: listing the account's current open orders in a dedicated view, including refresh behavior and the states shown when orders cannot be read.

### Modified Capabilities

- `ibkr-connection`: the "Read-only brokerage access" requirement says no feature issues order requests; it changes to allow querying open orders while still forbidding any request that places, modifies, or cancels an order.

## Impact

- **IBKR access:** adds one new read request, `reqAllOpenOrders`, on the shared connection. The connection stays `readonly=True`.
- **Order handling:** the app still never places, modifies, or cancels orders. No order-writing ib_async call is added, and a test guards this.
- **Setup impact:** the user chose to keep Read-Only API off, and the setup guidance now says to turn it off for the Orders view. That removes TWS's own block on order placement, so the app's code and the test that guards it are the remaining safeguard. Whether `reqAllOpenOrders` works with the setting on is untested, so the view keeps its could-not-read state for anyone who leaves it on.
- **API keys:** not touched.
- **Data leaving the machine:** none. Orders are not added to the AI Advisor's portfolio context.
- **Code:** `backend/services/ibkr_service.py`, new `backend/routers/orders.py`, `backend/main.py`, `src/lib/api.ts`, `src/types/index.ts`, new `src/hooks/useOpenOrders.ts`, new `src/pages/Orders.tsx` and `src/components/orders/`, `src/components/Sidebar.tsx`, `src/components/Layout.tsx`, `README.md`, new backend tests.
