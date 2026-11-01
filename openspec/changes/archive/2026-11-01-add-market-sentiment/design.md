# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`MacroService` streams quotes and refreshes bars per indicator, and `/api/macro/state` returns a flat `indicators` list that `Macro.tsx` lays out from `sections.ts`. `pandas` is a dev dependency only, so backend code can't use it.

A read-only probe on the user's paper account returned 752 daily bars for SPX, VIX, SPY, TLT, HYG, LQD, and RSP, using `TRADES` for the indexes and `ADJUSTED_LAST` for the ETFs. A prototype over 377 days gave:

| Measure | Result |
|---|---|
| Latest (Oct 30, 2026) | 24.0 |
| Mean / range | 52.9 / 20.8 to 82.6 |
| Share of days | Extreme Fear 2%, Fear 32%, Neutral 19%, Greed 44%, Extreme Greed 3% |

Latest components: momentum 10, volatility 14, safe haven 0, junk 2, breadth 94.

## Goals / Non-Goals

**Goals:**

- A transparent daily sentiment reading from data the app already has access to.

**Non-Goals:**

- Matching CNN's number, or fetching CNN's data.
- Put/call ratio and 52-week highs and lows. Neither has a confirmed daily IBKR series, and option volumes would need many market data lines.
- Using the score in signals, alerts, or the LLM filter.
- Backtesting it as a trading signal, or intraday updates.
- Saving score history.

## Decisions

### Own score, not CNN's feed

CNN's endpoint rejects automated requests, with a 418 reply saying the client is a bot, and no licensed API was found.

- *Alternative: disguise requests as a browser.* Lost because it deliberately bypasses a block.
- *Alternative: a third-party scraper API.* Lost because it adds an account and depends on the same blocked source.
- *Alternative: a link to CNN's page.* Lost because the number wouldn't be in the app. It can be added separately.

### Percentile against the past 252 days

Each component's latest value is ranked within its last year, which needs no assumptions about its distribution and puts all five on one scale.

- *Alternative: z-scores.* Lost because outliers distort them, and mapping them to 0–100 needs a further arbitrary step.
- *Alternative: min-max scaling, as in the Supertype article.* Lost because one extreme day compresses all other readings for a year.

### Breadth is shown but not scored

RSP/SPY shows who is leading, not whether the market is rising, so it runs against the market when big tech drives the move. On Oct 30 it read 94 while the others were near zero, lifting the score from about 6 to 24. It also tends to distort SOXL's context, since semiconductors move with big tech. The card keeps it as context, and the score and history leave it out.

- *Alternative: keep it in the score.* Lost for the reason above, and the user chose to remove it.
- *Alternative: remove it entirely.* Lost because the user wants to see it.

### Equal weights

- *Alternative: PCA or fitted weights, as Supertype's series suggests.* Lost because they're harder to explain, and a fit on a short history adds false precision.

### `ADJUSTED_LAST` for ETFs

TLT and HYG pay substantial income, so adjusted closes stop dividends reading as price drops.

- *Alternative: `TRADES` for all.* Lost because of false drops on ex-dividend dates. Indexes have no adjusted series, so they use `TRADES`.

### A separate calculation module

Pure functions in `sentiment.py` take daily closes and return the result, and `MacroService` adds one hourly task requesting two years per symbol, one after another. That covers 252 scored days plus the longest 125-day lookback. Results are in memory and rebuilt on connect.

- *Alternative: add seven `Indicator` entries.* Lost because they'd each stream and add cards the user didn't ask for, and five extra market data lines.
- *Alternative: use `pandas`.* Lost because it's dev-only, and these are short loops.

### A `sentiment` field on the existing state

`/api/macro/state` gains one object, polled by `useMacro` every 3 seconds, and the card reads it directly.

- *Alternative: a new endpoint.* Lost because it adds a second poll for the same view.

### Full-width card above the sections

- *Alternative: a card inside a section.* Lost because the score sums up the whole view, and its five components need more room.

### Explanation text comes from the backend

Each `Component` gains a `meaning`, sent with its `detail`, so one list defines what a component is and how it's described. The method and bands text stays in the card.

- *Alternative: a separate list in the renderer.* Lost because it could drift from the calculation.
- *Alternative: a dialog.* Lost because an inline section stays beside the values it explains.

## IBKR dependencies

Seven historical requests an hour, spaced one after another, sit well inside pacing limits. They use daily bars, so they work with markets closed, and depend on the same permissions the probe confirmed. Paper and live permissions can differ, so a live session reports any refused symbol on its component. Daily closes mean the score doesn't move during the session.

## Risks / Trade-offs

- [Breadth as context can still be misread] → It's marked as context only, and the explanation says why it's out of the score.
- [The score won't match CNN's] → The card says so, and the proposal states the differences.
- [Percentile rank is relative to one year] → A long calm period makes small moves score as extreme. This is inherent to the method.
- [Proxies differ from their names] → HYG/LQD is a price ratio, not a yield spread. Labels describe the actual input.
- [Reading it as a timing signal] → It's context only. It's not backtested, and alerts don't use it.
- [Hourly requests during a competing session can fail] → The component shows the error and retries next hour.
