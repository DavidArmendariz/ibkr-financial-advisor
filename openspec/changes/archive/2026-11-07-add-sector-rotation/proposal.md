# Proposal

## Why

The user wants to see where money is rotating between sectors, to put SOXL's moves in context. Is money leaving tech and semiconductors for defensive sectors, or coming back? A Relative Rotation Graph (RRG) shows that: each sector's strength against the market, and whether that strength is rising or fading, sorted into four quadrants (Leading, Weakening, Lagging, Improving).

A probe on Nov 6, 2026 got two years of daily and weekly bars for SPY and all 12 ETFs below through IBKR. On the weekly view, the approximation below put XLY, XLF, XLB, and XLRE in Leading, defensive XLV, XLP, and XLU in Weakening, and XLK and SMH in Lagging.

## What Changes

- A new **Sector Rotation** sidebar item, below Asia & Europe.
- A Relative Rotation Graph of the 11 SPDR sector ETFs (XLK, XLC, XLY, XLF, XLI, XLB, XLE, XLV, XLP, XLU, XLRE) and SMH (semiconductors), against SPY.
- Each ETF shows as a trail of its last few readings ending at its current position, so the direction of travel is visible.
- Weekly by default, with a daily option and an adjustable trail length.
- A table lists each ETF's quadrant, both readings, and how long it's been in that quadrant.
- Nothing else changes. It's context only and raises no alerts.

## Capabilities

### New Capabilities

- `sector-rotation`: the Relative Rotation Graph of sector ETFs against SPY.

### Modified Capabilities

None.

## Impact

- **IBKR access:** read-only. Adds one daily historical bar request per ETF and SPY (13), once per session.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none.
- **Code:** new `backend/rotation/` and router, `backend/main.py`, a new page, hook, and chart and table components, the sidebar, types, API client, README, `CLAUDE.md`, tests.
