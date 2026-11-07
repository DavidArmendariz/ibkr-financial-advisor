# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`IndicatorSet` in `backend/signals/indicators.py` updates EMA, Bollinger, RSI, relative volume, and VWAP per bar into `IndicatorValues`, which the live values card, chart, and saved signals read. Only SOXL streams. The account summary already returns `NetLiquidation` and `AvailableFunds`. Settings persist through `save_env_values` with a prefix per feature.

## Goals / Non-Goals

**Goals:**

- ATR visible for SOXL live, and for SOXS.
- A quick, correct long plan for either symbol.

**Non-Goals:**

- Placing, staging, or transmitting orders, including through TWS's own order ticket.
- Short trades. SOXS is the bearish trade.
- Stop and target lines on the chart, and ATR alerts.
- Trailing stops.

## Decisions

### Wilder's ATR, period 14

True range is the largest of high minus low, high minus the previous close, and the previous close minus low. It's smoothed like RSI, so it matches most charting tools.

- *Alternative: a simple average of true range.* Lost because it's less common, and wouldn't match what the user sees elsewhere.

### Intraday and daily ATR

Intraday ATR suits trades held minutes to hours, and daily ATR suits holding overnight. The basis is a setting, defaulting to intraday.

- *Alternative: intraday only.* Lost because a stop from 1-minute ATR is far too tight to hold overnight.

### SOXS from bars, polled while the planner is open

SOXS's 1-minute bars are fetched every 60 seconds only while the view is open, and daily bars for both once per session. SOXL uses the live pipeline for intraday ATR and price.

- *Alternative: stream SOXS.* Lost because a second stream adds a market data line and duplicates pipeline code for a calculator.
- *Alternative: use SOXL's ATR scaled for SOXS.* Lost because the two only mirror each other over a day, and their prices differ.

### Default the entry to the live ask

The planner streams bid and ask for both symbols while it's being viewed, and drops them after 2 minutes without a request. A buy fills at the ask, so the ask is the default entry, with the last price as the fallback. On Nov 5, 2026, TWS's Last field showed SOXL at $46.06 from a late off-exchange print while the bid and ask were $44.80 / $44.82, so the last trade isn't a reliable entry.

- *Alternative: the last trade.* Lost because of that example.
- *Alternative: keep quotes streaming all the time.* Lost because it would hold two market data lines for a view that's rarely open.

### Long only, sized by risk

Shares are the dollars at risk divided by the distance to the stop, rounded down. Risk defaults to 1% of net liquidation, because a fixed share count ignores how far the stop is.

- *Alternative: size by position value.* Lost because it makes the dollars at risk vary with volatility, which defeats ATR stops.

### Show values for TWS, with Copy

- *Alternative: place a bracket order.* Lost because of the project's rule, and needs the user's explicit decision to drop it.
- *Alternative: open TWS's order ticket.* Lost because the API has no way to stage an order without transmitting it from the app.

## IBKR dependencies

Two `reqMktData` lines, with the market data type set to real time right before subscribing, because Gamma and Macro set their own. One 1-minute SOXS request per minute while the planner is open, and one daily request per symbol per session. SOXS needs the same Network B subscription as SOXL, so live and paper share it. Outside market hours, prices are the last bar's, and the planner shows the data time.

## Risks / Trade-offs

- [A 1-minute SOXS price can be up to a minute old] → The data time shows.
- [Gaps can jump past a stop] → The planner says the stop is a price level, not a guaranteed fill.
- [ATR stops don't make a trade profitable] → The planner calculates and doesn't recommend.
