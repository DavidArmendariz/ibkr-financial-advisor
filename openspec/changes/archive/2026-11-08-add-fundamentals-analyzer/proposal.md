# Proposal

## Why

The user wants to judge a stock on its fundamentals inside the app: how expensive it is against its peers and its own past, how fast it grows, what analysts think, and what the news says. The app only covers prices and signals today. This analyzer is also the base for a later tracker list that flags undervalued stocks.

A probe on Nov 7, 2026 found that IBKR refuses fundamentals on this account (error 10358, "Fundamentals data is not allowed"), but serves news: 8 providers, including Dow Jones and Briefing.com Analyst Actions. The Finnhub key already saved for the earnings calendar returned 133 metrics for NVDA, 27 years of yearly multiples, 12 peers, analyst ratings, and company news. It refused price targets (HTTP 403) on the free plan, so analyst ratings take their place.

## What Changes

- A new **Fundamentals** sidebar item, below Sector Rotation. The user types a US ticker and sees:
  - **Valuation:** P/E, P/S, EV/EBITDA, EV/FCF, and P/B.
  - **Quality and growth:** revenue and EPS growth, margins, ROE, and debt to equity.
  - **Against peers:** each multiple next to the median of its Finnhub peers, with the peers listed.
  - **Against its own history:** each multiple next to its median over the last 5 fiscal years.
  - **Analyst ratings:** the latest strong buy, buy, hold, sell, and strong sell counts, with the month before for comparison.
  - **News:** recent headlines from IBKR (Dow Jones, and Briefing.com analyst actions such as upgrades and target changes) and from Finnhub.
- An **AI write-up** button sends that stock's figures and headlines to the AI provider configured in Settings, and shows a short bull case, bear case, valuation view, and what to watch. It is saved, and marked with the data's date.
- No alerts, signals, or orders.

## Capabilities

### New Capabilities

- `stock-fundamentals`: looking up one stock's valuation, quality, peer and history comparisons, analyst ratings, news, and an AI write-up.

### Modified Capabilities

None. It reuses the Finnhub key from the Calendar settings, as stored today.

## Impact

- **IBKR access:** read-only. Adds a contract lookup and a historical news request per lookup. Fundamentals aren't requested from IBKR, because the account refuses them.
- **Order handling:** not touched. The view only reads data.
- **API keys:** the existing Finnhub key and AI provider keys stay in the backend. The Finnhub key goes in a request header, so it's never in a logged URL. The renderer never sees either.
- **Data leaving the machine:** the ticker goes to Finnhub on each lookup, about 16 calls. On the AI write-up only, that stock's public figures and headlines go to the user's AI provider. Positions, orders, and account data are never sent.
- **Code:** new `backend/fundamentals/` and router, a SQLite table for saved write-ups, `backend/main.py`, a new page, hook, and components, the sidebar, types, API client, README, `CLAUDE.md`, tests.
