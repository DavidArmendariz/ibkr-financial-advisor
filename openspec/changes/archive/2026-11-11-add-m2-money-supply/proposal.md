# Proposal

## Why

The app shows prices, rates and sentiment, but not how much money is in the economy. M2 is the most-watched measure of it. Its growth tracks liquidity conditions, which affect inflation and how high-beta assets like semiconductors and SOXL get valued. The user wants M2 on its own page, with an explanation of what it is and how to read it.

## What Changes

- A new **M2 Money Supply** item in the sidebar, directly below Fundamentals, opens a new view.
- The view shows:
  - the latest M2 value, the month it covers, its change from the previous month and from a year earlier, when FRED last updated it, and when the next release is due;
  - a chart of the M2 level;
  - a chart of year-over-year growth, with a zero line so contractions stand out;
  - a range selector: 5 years, 10 years, 25 years, or all data since 1959.
- An explanation section on the same page covers what M2 is, what it includes, why it matters for markets, how to read each chart, and its limits.
- The data is FRED series `M2SL` (monthly, seasonally adjusted, billions of dollars). The backend fetches it with the FRED key the Calendar already uses, saves it locally, and refreshes it on a schedule. Without a key, the view says a FRED key is needed and links to Settings.

## Capabilities

### New Capabilities
- `money-supply`: the M2 Money Supply view, its data from FRED, its refresh and caching, the charts, and the explanation.

### Modified Capabilities
<!-- None. The FRED key requirement stays in event-calendar; this view reads the same key, and Calendar behavior doesn't change. -->

## Impact

- **Backend**: a new `backend/money_supply/` module (FRED fetch, YoY calculation, refresh loop), a router at `/api/money-supply`, and a SQLModel table that holds the saved observations. It's started and stopped alongside the other services in `backend/main.py`.
- **Renderer**: a new page `src/pages/MoneySupply.tsx`, a hook `useMoneySupply.ts`, components under `src/components/money-supply/`, a `'money-supply'` entry in the `AppTab` union, and a new item in Sidebar and Layout.
- **Dependencies**: none. It uses `httpx` and `recharts`, which the app already has.
- **Hard constraints**:
  - **IBKR access:** none. The feature makes no IBKR requests, works while disconnected, and can't place orders.
  - **API keys:** the FRED key stays in `.env` under `CALENDAR_FRED_API_KEY` and is only read by the backend. The renderer never receives it, and error messages leave out the request URL because the key is in it.
  - **Data leaving the machine:** requests to `api.stlouisfed.org` carry only the series ID and the key. This is the same exposure the Calendar already has.
