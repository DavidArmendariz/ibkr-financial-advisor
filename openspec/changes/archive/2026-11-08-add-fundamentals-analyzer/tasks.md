# Tasks

## 1. Data

- [x] 1.1 Add `backend/fundamentals/` with pure functions for the peer median (excluding the stock and duplicates, at least 3 peers), the 5-fiscal-year median (at least 3 years), the 20% cheaper flag, P/E not meaningful for losses, and the ticker check; test each, including the boundaries
- [x] 1.2 Add a Finnhub client that sends the key in a header and reports only endpoint and status, and parses metric, profile, quote, peers, recommendation, and company news; test parsing against probe-shaped replies, an unknown ticker, a 403, and a 429
- [x] 1.3 Add IBKR news: providers, then historical news for the stock, with headline prefixes stripped, merged with Finnhub news newest first and deduplicated; test merging, prefix stripping, and disconnection

## 2. Service, write-up, and API

- [x] 2.1 Add the lookup service with a one-hour cache per ticker and a refresh option; test caching, refresh, no key, and a rate limit that keeps earlier figures
- [x] 2.2 Add the AI write-up with a JSON schema, a 60-second timeout, and a `FundamentalsAnalysis` table; test that only the stock's public data is sent, invalid replies, no provider, and that a saved write-up comes back with its data date
- [x] 2.3 Add `GET /api/fundamentals/{ticker}` (with `refresh`) and `POST /api/fundamentals/{ticker}/analysis`; test them, including a rejected ticker, and that no order calls exist

## 3. View

- [x] 3.1 Add the Fundamentals tab below Sector Rotation, with a hook, types, and API calls, and remember the last ticker
- [x] 3.2 Build the header and the valuation table, with each multiple, its peer median, its 5-year median, and the cheaper markers in text, plus quality and growth figures and the peers list
- [x] 3.3 Add analyst ratings for this month and last, the merged news list, the AI write-up panel, the no-key and error states, and the data-source note

## 4. Docs and verification

- [x] 4.1 Update the README (feature, API) and `CLAUDE.md` (capability list, layout)
- [x] 4.2 Verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 4.3 Look up NVDA and a loss-making stock against the live data, and check the view in a browser at full and narrow widths, with saving and the AI call mocked

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
- Then propose the fundamentals tracker list.
