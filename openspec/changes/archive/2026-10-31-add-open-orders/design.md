# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

The app holds one shared `ib_async` connection, opened with `readonly=True`. That flag only skips ib_async's startup order requests (`ibkr_service.py:41`); the block on order placement comes from the **Read-Only API** setting in TWS. The README tells users to leave that setting on, and says the write-access pop-up appears when something asks TWS for orders.

Whether the setting blocks `reqAllOpenOrders` is unconfirmed. IBKR's docs describe Read-Only mode as allowing market data and account information while blocking trading activity, and they say one order-related call is rejected in that mode, but they do not cover this request. TWS was not running when this was written, so it could not be tested.

## Goals / Non-Goals

**Goals:**

- Show open orders across all clients, with the fields in the spec.
- Behave safely if TWS refuses the request: a clear message, not a false empty list or repeated pop-ups.

**Non-Goals:**

- Order actions of any kind.
- Order history, fills, or executions.
- Sending orders to the AI Advisor or to signals.
- Changing TWS settings, or the app's `readonly=True` connection.
- Breaking down combo orders into legs. They show under the symbol IBKR reports.

## Decisions

### Read with `reqAllOpenOrdersAsync`

It returns orders from every client, including manual TWS orders, as the spec requires.

- *Alternative: `reqOpenOrdersAsync`.* Lost because it returns only this client's orders, and the app places none, so the list would always be empty.
- *Alternative: `reqAutoOpenOrders`.* Lost because it needs client ID 0 and binds manual orders, which changes their order IDs. That is a side effect on orders, and IBKR says it is rejected in Read-Only mode.
- *Alternative: the claude.ai IBKR connector or Client Portal API.* Lost because the first is not available to the desktop app, and both would add a second login path to a local-first app.

### Treat a timeout as "could not read"

A new `get_open_orders()` wraps the request in a 5 second timeout, like `_snapshot`. ib_async treats 321 as a warning and does not end the pending request, so a refusal looks like a request that never finishes. `accountSummaryAsync` and `reqPositionsAsync` have this same no-timeout problem. The endpoint returns `{"available": false, "orders": []}` in that case and `{"available": true, "orders": [...]}` on success. It returns 503 when disconnected, like the portfolio routes.

- *Alternative: an HTTP error for refusal.* Lost because it is an expected state the UI renders, not a failure, and it would have to be separated from "backend unreachable" anyway.
- *Alternative: listening for error 321 specifically.* Lost because the exact refusal code is unverified and a timeout must be handled regardless.

### Serialize requests with a lock

ib_async keys this request by a single `"openOrders"` name, and a second concurrent `startReq` replaces the first one's future, leaving it unanswered. An `asyncio.Lock` prevents that, for example between polling and a manual refresh or React's double mount in dev.

- *Alternative: rely on the UI not overlapping.* Lost because the double mount makes overlap routine in dev.

### Exclude only finished orders

The list removes `DoneStates` minus `Inactive`, leaving out only filled and cancelled orders. `Trade.isActive()` leaves out `PendingCancel` and `Inactive`, but an order waiting on a cancel may still fill. ib_async's `DoneStates` includes `Inactive`, but an `Inactive` order is one the user needs to see.

- *Alternative: `openTrades()` from ib_async's local state.* Lost because with `readonly=True` that state is never synced at connect, so it would miss orders.
- *Alternative: plain `DoneStates`.* Lost because it hides `Inactive` orders.

### Map unset prices to null

ib_async represents an unset price as `UNSET_DOUBLE` (`sys.float_info.max`). The service converts it, and 0 on a price that does not apply to the order type, to `null`, so the table shows an empty field rather than an enormous number or a misleading 0.00.

- *Alternative: format in the renderer.* Lost because the value is an ib_async detail and should stop at the backend.

### Stop polling in the hook after a refusal

`useOpenOrders`, mounted only by the Orders page, polls every 15 seconds like `usePortfolio`. On `available: false` it stops the timer until the user refreshes or reopens the view.

- *Alternative: a backend cooldown.* Lost because the rule is simpler in the only client, and a manual refresh must always go through.
- *Alternative: fetch in `Layout` alongside the portfolio.* Lost because the request would run on every view, which could raise pop-ups for users who never open Orders.

### New `orders` router and tab

`GET /api/orders/open` lives in a new `routers/orders.py`, following the one-router-per-feature layout. The `AppTab` union gains `'orders'`.

- *Alternative: a section on the Dashboard.* Lost because the user asked for a sidebar item.

## IBKR dependencies

- **Permissions:** no market data subscription is needed, since no prices are requested for orders. Read-Only API may block the request (see Risks).
- **Pacing:** one request every 15 seconds while the view is open is well within limits and uses no market data lines.
- **Market hours:** orders are readable at any time. Status may read `PreSubmitted` outside trading hours.

## Risks / Trade-offs

- [TWS may refuse the request with Read-Only API on] → The user keeps the setting off and the setup guidance says to. The could-not-read state remains for anyone who leaves it on, and has only been tested with mocked responses.
- [Turning off Read-Only API removes TWS's block on order placement, leaving only the app's code as the safeguard] → The view states this, and a test fails if order-writing ib_async calls appear in `backend/`.
- [The pop-up appears once per view open while refused] → Polling stops after the first refusal.
- [A slow TWS is reported as a refusal] → The message says "could not be read", and refresh retries.
- [A late reply after a timeout lands in the abandoned result list] → Harmless, because the next request starts a new list.

## Open Questions

- Does `reqAllOpenOrders` work with Read-Only API on? It was not tested, because the user chose to keep the setting off. Both outcomes are handled, so the answer does not change the specs or approach.
