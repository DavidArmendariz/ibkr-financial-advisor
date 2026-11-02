# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

## Goals / Non-Goals

**Goals:**

- All 12 stocks readable and comparable at a glance.

**Non-Goals:**

- Sorting, or changing what the backend fetches.

## Decisions

### One table with a Market column

Rows stay in the existing market order, with the market named on each row.

- *Alternative: one small table per market.* Lost because columns wouldn't line up across tables, which is the point of a table.

### Keep the percent change as its own column

- *Alternative: combine change and percent as on cards.* Lost because stocks trade in different currencies, so percent is the only figure that compares across rows.

### Keep requesting 5-minute bars for stocks

- *Alternative: drop them now that nothing draws them.* Lost because they still supply the latest price and data time.

## IBKR dependencies

None. Requests are unchanged.

## Risks / Trade-offs

- [Wide table on a narrow window] → The table scrolls inside its own frame, and the page doesn't.
