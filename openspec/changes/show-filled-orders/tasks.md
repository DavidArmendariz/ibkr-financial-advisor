# Tasks

## 1. Backend

- [x] 1.1 Add `get_filled_orders` using `reqExecutions`, grouped per order, and `GET /api/orders/filled`
- [x] 1.2 Save fills to a `TradeFill` table by execution ID, in a background task and on request, with live and paper apart
- [x] 1.3 Test saving, restarts, no double counting, late commissions, modes, grouping, the average price, unset commission and P&L, newest first, timeout, and the connection check

## 2. View

- [x] 2.1 Add a filled orders hook, table, and section, rename the page, and make Refresh cover both

## 3. Verification

- [x] 3.1 Update the README, and verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 3.2 Confirm the real SOXS fill shows in the browser

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
