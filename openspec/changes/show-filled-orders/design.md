# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

On Nov 1, 2026, live TWS with Read-Only API on refused `reqCompletedOrders` with error 321. `reqExecutions` worked and returned the SOXS fill, with the same fill for the default request and a 7-day time filter.

## Goals / Non-Goals

**Goals:**

- See filled orders on live and paper, including with Read-Only API on.
- Keep a permanent history, because IBKR only returns recent fills.

**Non-Goals:**

- Cancelled orders.

## Decisions

### Use executions

- *Alternative: `reqCompletedOrders`.* Lost because Read-Only API refuses it, and it would need live protections turned off.
- *Alternative: the account connector.* Lost because the app reads IBKR through TWS only.

### Group executions by order

A partly filled order arrives as several executions. Rows combine them by permanent order ID, with a volume-weighted average price, and show the latest fill's time.

- *Alternative: one row per execution.* Lost because the user thinks in orders.

### Save each fill by its execution ID

A `TradeFill` row per execution, with live and paper kept apart. A background task saves new fills every minute while connected, and opening Orders also saves. Commission and P&L fill in when reported, and a blank reply never clears them.

- *Alternative: save only when Orders is open.* Lost because a fill could leave IBKR's window unseen.
- *Alternative: save per order.* Lost because execution IDs prevent double counting, and orders can fill in parts across refreshes.
- *Alternative: store the account number.* Lost because the mode is enough, and it avoids keeping an identifier.

### Show commission and P&L only when IBKR reports them

Commission reports arrive after the reply, and ib_async stores them on its own fill records while each `reqExecutions` reply holds blank copies. The list reads the stored records, and empty values show as empty rather than as zero, so a new fill can take one refresh to get them.

- *Alternative: show zero.* Lost because it reads as a free trade.

## IBKR dependencies

`reqExecutions` on the shared connection, every minute while connected, and every 15 seconds while the view is open. TWS decides how far back it answers, so older fills may be missing.

## Risks / Trade-offs

- [Fills are missed if the app isn't connected during IBKR's window] → Stated in the README.
- [Dev and packaged apps have separate databases] → Accepted. Each keeps its own history.
- [The newest 2,000 fills show] → Older ones stay saved.
- [Multiple accounts are combined] → Accepted: the open list works the same way.
