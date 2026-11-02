# Proposal

## Why

The KOSPI 200 lags Samsung and SK Hynix, and the estimate added for that mixed the official value with an ETF-based one. The user asked for KODEX 200 to have its own card and for the estimate to go.

## What Changes

- KODEX 200 ETF becomes a visible card in the Indexes section, directly after the KOSPI 200, with its own price in KRW, change, sparkline, and delay.
- The KOSPI 200 estimate is removed, so the KOSPI 200 card shows only the real index.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `global-markets`: adds the KODEX 200 card and removes the estimate.

## Impact

- **IBKR access:** unchanged. The ETF was already requested.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none.
- **Code:** `backend/global_markets/`, `src/components/global-markets/MarketCard.tsx`, `src/types/index.ts`, README, tests.
