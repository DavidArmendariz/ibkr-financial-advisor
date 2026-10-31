# Proposal

## Why

The Macro view is a flat list of 11 cards, with each index's futures card separated from its spot card, so comparing the S&P 500 with its futures means reading across the grid. Grouping related indicators makes the view quicker to scan.

## What Changes

- Group the Macro view into three labelled sections, in this order: **Equity indexes**, **Rates & volatility**, and **Commodities & currency**.
- Replace the separate futures and spot cards for the S&P 500, Nasdaq 100 and Dow with one card per index, going from 11 cards to 8. All 11 indicators stay.
- In a combined card, futures come first and own the sparkline, contract, and main freshness label. The spot index gets a smaller line with its own value, change, freshness, and error.
- No indicator is added or removed, and the data, refresh rates, and API stay the same.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `macro-indicators`: changes how indicators are arranged and which card shows them, and adapts the change, sparkline, freshness, and error requirements to combined index cards.

## Impact

- **IBKR access:** unchanged. The same market data and historical requests run, including bars for spot indexes, which still supply closed-market values.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** unchanged.
- **Code:** `src/pages/Macro.tsx`, `src/components/macro/IndicatorCard.tsx`, new `src/components/macro/IndexCard.tsx`, new `src/components/macro/sections.ts`, and `README.md`. The backend and `GET /api/macro/state` do not change.
