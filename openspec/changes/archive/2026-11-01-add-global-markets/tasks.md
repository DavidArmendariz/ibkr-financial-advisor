# Tasks

## 1. Backend

- [x] 1.1 Add `backend/global_markets/instruments.py` with the 16 contracts from the design
- [x] 1.2 Add pure functions for the previous close, change, open state, and whether an instrument is due for a refresh; test them, including a closing auction difference, a Tokyo lunch break, a holiday, and a session changing
- [x] 1.3 Add a service that resolves contracts, reads hours, and refreshes due instruments one at a time, without `reqMktData` or `reqMarketDataType`; start and stop it with the app
- [x] 1.4 Test with mocks: a refused instrument leaves others updating and shows the error, an empty reply keeps values, closed markets aren't requested, disconnection marks values stale, and no order or market data line call exists
- [x] 1.5 Add `GET /api/global-markets` with a test

## 2. View

- [x] 2.1 Add the `global-markets` tab to `AppTab`, `Sidebar.tsx` directly below Macro, and `Layout.tsx`
- [x] 2.2 Add a polling hook, API call, and types
- [x] 2.3 Add the page and card with the sections, grouping, open or closed state, local data time, sparkline, errors, and not-connected state

## 3. Docs

- [x] 3.1 Update the README, and add `global-markets` and the new package to `CLAUDE.md`, plus the `SMART` and streaming gotchas

## 4. Verification

- [x] 4.1 Verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 4.2 Look at the view in a browser, including a narrow window
- [x] 4.3 Confirm each of the 16 cards against real IBKR data, and check two changes by hand
- [ ] 4.4 Check Taiwan and Europe during their open hours, confirming intraday bars arrive and noting their lag
  - Taiwan confirmed on Nov 2, 2026 at 09:37 Taipei: bars arrive about 22 minutes behind. Europe not yet checked; the change was archived with this open at the user's choice.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
