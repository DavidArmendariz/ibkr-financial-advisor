# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`GET /api/macro/state` returns a flat list of 11 indicators, each with its own value, change, freshness, error, and sparkline, and `Macro.tsx` renders one `IndicatorCard` per entry. Everything the new layout needs is already in that response, keyed by `key` (`es`/`spx`, `nq`/`ndx`, `dow`/`dji`).

## Goals / Non-Goals

**Goals:**

- Arrange the view by section, with one card per index.
- Keep each indicator's own freshness and error visible on a combined card.

**Non-Goals:**

- Adding or removing indicators, or changing any data, refresh rate, or API field.
- Fixing the leftover 10197 error on a card while a market is closed. That is a separate backend bug.
- User-configurable sections or card order.

## Decisions

### Define the layout in the renderer

A new `sections.ts` holds a constant listing each section's label and its cards, where an index card names its futures and spot keys. `Macro.tsx` looks indicators up by key.

- *Alternative: add a `section` field to the API.* Lost because grouping is presentation only, and the change would otherwise stay out of the backend entirely.

### Show unlisted indicators instead of dropping them

Any indicator the layout doesn't name renders in a final "Other" section, so a new backend indicator can't silently disappear from the view.

- *Alternative: render only what the layout names.* Lost because a forgotten layout entry would hide data with no sign of it.

### One card per index, with spot as a secondary line

A new `IndexCard` shows the futures like an `IndicatorCard`, then a compact spot line with value, change, freshness, last update, and any error.

- *Alternative: two separate cards side by side within an index group.* Lost because it keeps all 11 cards and three pairs don't fit a three-column grid.
- *Alternative: a full-width table row per index.* Lost because it drops the sparkline, which is the card's quickest read.

### The sparkline follows the futures

Futures trade nearly around the clock, so their sparkline stays useful when the spot index is closed. The backend keeps requesting spot bars because closed-market spot values come from them; they just aren't drawn.

- *Alternative: a toggle or two sparklines.* Lost because the two lines look nearly identical, so it adds controls and height for little information.
- *Alternative: stop requesting spot bars.* Lost because closed cards would lose their values.

### Share the card pieces

The label, freshness row, and error row move out of `IndicatorCard` into small shared components within its file or folder, so both cards stay consistent. `IndicatorCard`'s behavior doesn't change.

- *Alternative: copy the markup into `IndexCard`.* Lost because the freshness and stale rules would drift apart.

## IBKR dependencies

None change. Spot indexes still depend on CBOE and CME index data, and the Dow Jones index can still show error 162 without that permission. Requests and pacing stay the same, and market hours affect only the labels each value already has.

## Risks / Trade-offs

- [The spot line crowds the card at narrow widths] → Its fields wrap, and this is checked at narrow and normal widths.
- [Index cards are taller than others in a row] → The grid stretches cards in a row to equal height, and all three cards in that section have the same shape.
- [A long Dow error makes one card taller] → The whole row stretches with it, and the error stays beside the spot line.
- [Spot sparklines are no longer visible] → Accepted, since they closely track the futures shown.
