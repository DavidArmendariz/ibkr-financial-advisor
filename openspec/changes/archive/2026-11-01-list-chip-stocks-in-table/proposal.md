# Proposal

## Why

Twelve chip stocks as sparkline cards take several screens of scrolling and are hard to compare. The user asked for them as a list in a table instead.

## What Changes

- Chip stocks show in one table, one row per stock, grouped by market in the existing order, with no sparklines.
- Index cards keep their sparklines.
- The backend and its data don't change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `global-markets`: chip stocks move from cards to a table.

## Impact

- **IBKR access:** unchanged.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none.
- **Code:** `src/pages/GlobalMarkets.tsx`, `src/components/global-markets/`, README.
