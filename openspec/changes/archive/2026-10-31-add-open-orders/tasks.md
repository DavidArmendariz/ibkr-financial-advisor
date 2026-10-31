# Tasks

## 1. Backend

- [x] 1.1 Add `get_open_orders()` to `backend/services/ibkr_service.py` using `reqAllOpenOrdersAsync` with a lock and a 5 second timeout, returning `available` and the mapped orders; verify with tests in `tests/test_orders.py` for a normal reply, a timeout, and overlapping calls
- [x] 1.2 Map each trade to the fields in the spec, with option expiry, strike and right, unset or inapplicable prices as `null`, and filled or cancelled orders removed; verify with tests covering a stock limit order, an option order, a market order, `PendingCancel`, `Inactive`, and `Filled`
- [x] 1.3 Add `backend/routers/orders.py` with `GET /api/orders/open`, returning 503 when disconnected, and register it in `backend/main.py`; verify with a test of the 503 and with a request to the running dev backend
- [x] 1.4 Add a test that scans `backend/` and fails on `placeOrder`, `cancelOrder`, `reqGlobalCancel`, or `reqAutoOpenOrders`; verify it passes now and fails against a temporary sample containing `placeOrder`
- [x] 1.5 Update the comment at `ibkr_service.py:41` so it covers why orders are read on demand; verify `uv run pytest` passes

## 2. Renderer

- [x] 2.1 Add `OpenOrder` and `OpenOrdersState` types, `'orders'` to `AppTab`, and `getOpenOrders` in `src/lib/api.ts`; verify `npx tsc --noEmit -p .` passes
- [x] 2.2 Add `src/hooks/useOpenOrders.ts` with 15 second polling while mounted, stopping on `available: false`, and resuming on manual refresh, on remount, and after reconnecting; verify in the browser that requests stop when leaving the view
- [x] 2.3 Add `src/pages/Orders.tsx` and `src/components/orders/OrdersTable.tsx` with a refresh control and the empty, not connected, and could-not-read states, with no order actions; verify each state in the browser with Playwright using mocked API responses
- [x] 2.4 Add Orders below Dashboard in `src/components/Sidebar.tsx` and render the page in `src/components/Layout.tsx`; verify in the browser that it opens and shows as selected

## 3. Real TWS check and documentation

- [x] 3.1 With paper TWS running and Read-Only API off, which is the setting the user chose to keep, open the view with one working order and verify that it loads
- [x] 3.2 Confirm that an order placed manually in TWS appears; a refusal by real TWS is not tested, so the refusal state is covered by mocked responses only
- [x] 3.3 Update the README's feature list, API reference, Read-Only API row, and the write-access pop-up note, and the setup checklist in `src/components/ConnectionGuard.tsx`, to say Read-Only API is off for the Orders view; verify no text still tells users to leave it on

## 4. Integration checks

- [x] 4.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 4.2 Look at the Orders view and the sidebar in a browser at http://localhost:5273, with screenshots kept in the scratchpad, and verify layout at normal width and with the sidebar hidden

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
