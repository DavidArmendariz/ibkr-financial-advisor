# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

- **Probe on Nov 7, 2026:**
  - IBKR `reqFundamentalData` returned error 10358 for every report type.
  - `reqNewsProviders` listed BRFG, BRFUPDN, DJ-N, DJ-RT, DJ-RTA, DJ-RTE, DJ-RTG, and DJNL, and `reqHistoricalNews` returned NVDA headlines. Headlines carry a `{A:…:L:en}` prefix that needs stripping.
  - On Finnhub, with the saved key:
    - `stock/metric?metric=all` gave 133 TTM and annual fields, plus yearly `series` for pe, ps, evEbitda, and pb (27 years for NVDA and KO). The quarterly multiples were empty, except pb.
    - `stock/peers` returned 12 symbols, including NVDA itself and MRVL twice.
    - `stock/profile2`, `stock/recommendation`, `company-news`, and `quote` worked. `stock/price-target` returned 403.
- **Existing code to reuse:**
  - The calendar already stores `CALENDAR_FINNHUB_API_KEY` and fetches with httpx, reporting only the error type and status, because the URL carries the key.
  - Signal analyses already call the configured provider through `llm_filter.resolve_provider` and the `LLMProvider.complete(…, schema=…)` protocol, and save results to SQLite.

## Goals / Non-Goals

**Goals:**

- One lookup shows enough to judge whether a stock looks cheap, and why.
- Lay out the comparisons so the later tracker can reuse them per stock.

**Non-Goals:**

- Non-US stocks, which Finnhub's free plan doesn't cover.
- Price targets, discounted cash flow models, or full financial statements.
- A watchlist or tracker, which is the next proposal.
- Reading full news articles. Headlines and links only.

## Decisions

### Finnhub for figures, IBKR and Finnhub for news

Figures come from Finnhub `stock/metric`, `profile2`, `quote`, `peers`, and `recommendation`. News merges IBKR historical news, last 7 days, up to 30 headlines across all subscribed providers, with Finnhub `company-news`. Duplicates are dropped by normalised headline.

- *Alternative: IBKR fundamentals.* Lost because the account refuses them (10358), and they'd need a paid data subscription.
- *Alternative: Finnhub news only.* Lost because IBKR adds Briefing.com analyst actions and Dow Jones at no cost.

### Peer and history medians as pure functions

A module computes:

- The peer median per multiple, over peers with a positive value. It excludes the stock and duplicates, and needs at least 3 peers.
- The 5-fiscal-year median from the yearly series. It ignores non-positive values and needs at least 3 years.
- A "cheaper" flag at 20% or more below each median.

P/E with negative earnings is "not meaningful". EV/FCF has no yearly series, so it shows peers only. The tracker will reuse these functions.

- *Alternative: averages.* Lost because one outlier peer, such as a 400× P/E, would skew a mean.
- *Alternative: industry-wide medians.* Lost because Finnhub's free plan has no industry aggregates, and its peer list is the closest substitute.

### Request budget and caching

A lookup is about 16 Finnhub calls: metric, profile, quote, peers, recommendation, news, and one metric call per peer, up to 10 peers. That fits under the free plan's 60 calls a minute. Results are cached in memory per ticker for an hour, and a Refresh button bypasses the cache. On HTTP 429, the lookup stops and says to try again in a minute. The figures already shown stay.

- *Alternative: store lookups in SQLite.* Lost because figures go stale, and an hour in memory covers repeat views. Only the AI write-up is saved.

### Finnhub key in a header

Requests send the key as `X-Finnhub-Token`, so it never appears in a URL, a log, or an error message. Errors report the endpoint name and status only.

- *Alternative: the `token` query parameter, as the calendar uses.* Lost because it puts the key in the URL. The calendar is unchanged.

### AI write-up, saved per ticker

The prompt gets the computed figures, flags, ratings, and up to 15 headlines as JSON. It asks for `bull_case`, `bear_case`, `valuation_view`, and `watch`, with a JSON schema and a 60-second timeout, like signal analyses. The result is saved in a `FundamentalsAnalysis` table, keyed by ticker, with the data timestamp, provider, and model. A new request replaces it.

- *Alternative: write automatically on every lookup.* Lost because it spends a provider call each time, and the user asked for it on demand.
- *Alternative: a buy or sell verdict.* Lost because the app gives context, not advice. The prompt avoids recommendations and order sizes.

### Ticker input

The input is uppercase letters, digits, dots, and dashes, up to 10 characters, validated in the backend before any request. The last ticker is remembered in the renderer's localStorage.

- *Alternative: a symbol search.* Lost because Finnhub's search adds calls and non-US noise. An unknown ticker gets a clear message instead.

## IBKR dependencies

`reqContractDetails` and then `reqHistoricalNews`, once per lookup, and only when connected. News providers depend on the account's subscriptions. Works with the market closed. No market data lines are used.

## Risks / Trade-offs

- [Finnhub's free plan may change or tighten its limits] → Errors are shown per source, and the 429 handling keeps the view usable.
- [Peer lists can be odd, such as a conglomerate's peers] → The peers are listed, so the user can judge the comparison.
- [The AI write-up can sound confident] → Its data date is shown, the figures sit beside it, and the view says it isn't investment advice.
- [Yearly history lags a fast-changing company] → Labelled "5 fiscal-year median", with the trailing figure beside it.
