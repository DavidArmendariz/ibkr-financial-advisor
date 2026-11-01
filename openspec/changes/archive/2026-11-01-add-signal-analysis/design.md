# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

Each `SignalEvent` stores the indicators and last 20 bars in its payload. `get_historical_bars` always requests up to now, and `llm_filter.py` has provider classes capped at 256 output tokens and tied to the filter's decision schema, with Anthropic using structured output. New tables come from `create_all` at startup. The renderer's axios client has a 10 second timeout. Signal History reads pages from `GET /api/signals/history`, and `SignalTable` is shared with the Signals view.

## Goals / Non-Goals

**Goals:**

- A pre-mortem that can't see the future, and a post-mortem grounded in measured outcomes.

**Non-Goals:**

- Automatic or batch analysis, or analysis from the notification.
- Positions, news, gamma, or macro context. None is stored as it was at signal time, so using today's values would leak hindsight.
- A chat about the signal, or statistics across signals.
- Order actions.

## Decisions

### Enforce the time limit in code, not the prompt

`analysis.py` filters bars to those that closed at or before the signal's time before building the pre-mortem request, and the function has no access to later data. A test asserts this.

- *Alternative: send all bars and tell the model to ignore later ones.* Lost because a model can't reliably ignore what it has read.

### Bars come from IBKR on demand

One historical request gets the signal's 1-minute session bars, with `get_historical_bars` gaining an end time. The pre-mortem filters them, and the post-mortem also uses the later ones. Bars aren't saved. Outcomes use the 1-minute bars, while the provider receives them grouped into 5-minute bars, since a full session of 1-minute bars is about 1,000 rows per click.

- *Alternative: store every session's bars.* Lost because it adds a data store for a feature that only needs them on click, and IBKR history covers past signals.
- *Alternative: use only the saved 20 bars.* Lost because 20 minutes is too little context for a considered analysis, and the post-mortem needs later bars anyway.

### The backend computes outcomes

`analysis.py` computes returns at each horizon, the largest gain and loss, and whether price returned to its starting level. Entry is the signal's price. Short figures are the negative of long figures, excluding costs.

- *Alternative: let the model read the bars.* Lost because models miscalculate, and these numbers are the point of the post-mortem.

### Direction by trigger

Upward crosses and band above are judged long. Volume has no direction, and band below can read as breakdown or stretched, so both are judged both ways.

- *Alternative: judge everything as long.* Lost because the app's only trades would be long, but it would misjudge alerts that don't imply a buy.

### Extend the provider call, not a second client

`complete()` gains `max_tokens` and an optional `schema`, with the filter's values as defaults. Analysis uses the same provider and model as the filter, 1,500 tokens, and 60 seconds. Replies are JSON validated against each kind's fields.

- *Alternative: a separate model setting.* Lost because the existing per-provider model works, and more settings add little.
- *Alternative: free-form markdown.* Lost because the verdict needs a dependable field.

### A separate table, keyed by signal and kind

`SignalAnalysis(signal_id, kind, created_at, provider, model, result)` holds the latest of each kind. A successful rerun replaces it, in one write after the reply validates. `GET /api/signals/history` includes each signal's analyses, read in one query per page.

- *Alternative: store it in the signal's payload.* Lost because the spec keeps the saved signal unchanged, and rewriting JSON is more fragile.
- *Alternative: keep every run.* Lost because the user needs the latest result, and history adds UI and storage for no stated use.

### `POST /api/signals/{id}/analysis/{kind}` returns when finished

The renderer's call sets a 90 second timeout, and a per-signal, per-kind in-flight set answers a duplicate with 409. Errors return as `detail` text the panel shows.

- *Alternative: a background job with polling.* Lost because a single request is simpler, and an analysis is short and user-initiated.

### Row actions only in Signal History

`SignalTable` gains an optional `renderDetails` prop, so the Signals view stays the same. The history page shows the buttons and `SignalAnalysisPanel` in an expandable row.

- *Alternative: a separate analysis page.* Lost because the result belongs next to its signal.

## IBKR dependencies

Each click makes one historical data request. It needs the SOXL stock data subscription already required for signals, and pacing is unaffected at human click rates. Historical bars work with markets closed, but 1-minute history isn't unlimited, so very old signals can fail with a reported error. It needs the IBKR connection, unlike the rest of Signal History, and the app's lock screen covers disconnects.

## Risks / Trade-offs

- [The pre-mortem's model knows general history, and could recognize a famous date] → Limited for one stock's intraday bars. The time limit covers supplied data only, and the result says so.
- [The verdict can sound more certain than it is] → It's labelled as AI analysis, and the figures show beside it. It's neither advice nor a backtest.
- [Costs depend on clicks] → One call per click, with 1,500 output tokens at most, and no automatic runs.
- [The saved snapshot of a test row has no bars] → The analysis uses IBKR bars and reports an error if they're unavailable.
- [Stored signal time could be misread] → Times are UTC, as in `_record`, and a test covers the boundary bar.
