# Design

## Context

Signals are saved in `SignalEvent`, with `time` as the bar close. The post-mortem in `backend/signals/analysis.py` already fetches a day's 1-minute bars and computes returns, but only on request, at 15, 30, and 60 minutes, and with the provider involved. `SignalService._loop` runs every second and owns the stream. The live pipeline's bars are bounded, so they can't cover older signals.

## Goals / Non-Goals

**Goals:**

- Automatic figures for every signal, new and old.
- Results per trigger that are honest about baseline and sample size.

**Non-Goals:**

- Changing or turning off triggers based on results.
- Calling any result a win or a loss.
- Stops, targets, position sizes, or simulated P&L.
- Splitting results by LLM decision, settings in force, or time of day. These can follow once there's enough data.
- Charts. A table reads better for comparing exact figures across triggers.

## Decisions

### Measure direction neutrally

Report signed moves and the share of moves up, with no hit rate.

- *Alternative: a hit rate per trigger.* Lost because relative volume, VWAP band below, and the RSI triggers imply no direction, as the post-mortem spec already recognizes. A hit rate would invent one. This replaces the "hit rate" in the original idea with share up.

### Include a baseline row

Each measured day also stores totals from every regular-hours minute. The baseline row combines those days.

- *Alternative: triggers only.* Lost because a leveraged ETF in an uptrend makes almost any trigger look good. This is the main addition beyond the original request, and it adds a table.

### Fixed 5, 15, and 30 minute horizons

- *Alternative: reuse the post-mortem's 15, 30, and 60.* Lost because the user asked for shorter day-trading horizons. The post-mortem keeps its own figures.
- *Alternative: configurable horizons.* Lost because changing them would need every signal measured again.

### Measure in a background pass

A separate task checks every 5 minutes for signals over 30 minutes old with no saved figures, and fetches one ET day of 1-minute bars per pass, newest first. A failed request leaves those signals pending for a later pass. Bars are requested as regular-hours only.

- *Alternative: compute from the live pipeline's bars.* Lost because that misses older signals and anything during a stream gap.
- *Alternative: compute when the page opens.* Lost because results would depend on visiting the view, and old days would hold up the page.

### Take the entry from the fetched bars

The entry is the close of the fetched bar ending at the signal's time, and the signal's own record isn't used for it. Historical bars are split-adjusted, so a saved price from before a split would produce a huge false move. If no bar ends at that time, the signal is not available.

- *Alternative: the saved signal price, as the post-mortem does.* Lost because of that split risk. The two normally match.

### Find a finished session's close from its own bars

A finished day's close is the end of its last regular-hours bar. Today's close comes from the calendar until the session ends.

- *Alternative: `SessionCalendar`.* Lost because `liquidHours` only reaches around today, so a past half-day would be treated as closing at 16:00.

### Confirm a day is gone before giving up on it

`reqHistoricalDataAsync` returns an empty list on errors too. An empty reply for a finished day only marks it not available if a follow-up request for recent bars returns data, proving IBKR is serving bars.

- *Alternative: treat every empty reply as expired.* Lost because a competing live session or a failed request would permanently hide good days.
- *Alternative: mark after several empty replies.* Lost because an outage can outlast any count.

### Keep figures in new tables

`SignalOutcome` has one row per signal: status, the three moves, and the largest up and down. `OutcomeBaseline` has one row per day. It stores that day's figures as JSON lists, about 390 numbers each, because medians can't be combined from daily totals.

- *Alternative: add them to `SignalEvent.payload`.* Lost because the spec keeps that record unchanged, and aggregating would mean parsing every payload.

### Add one results endpoint

`GET /api/signals/outcomes` returns the per-trigger table, the baseline, and the pending count. `/history` records gain an `outcome` field. Results are computed in the backend, and the renderer only displays them.

- *Alternative: compute in the renderer.* Lost because the renderer only holds a page of signals.

## IBKR dependencies

Uses `reqHistoricalData` for 1-minute TRADES on the shared connection, the same call as post-mortems, needing the same data subscriptions. One request per 5-minute pass, plus a confirming request after an empty reply, stays far under pacing limits, and a 60-day backfill takes about 5 hours of connected time. It works with the market closed. How old 1-minute bars can be is up to IBKR, so days it no longer has become not available. It doesn't call `reqMarketDataType`, so other features aren't affected.

## Risks / Trade-offs

- [Results mix different settings, since thresholds change over time] → Stated as a limit. Splitting by settings is a later step.
- [Signals cluster, so 30 alerts in a burst aren't 30 independent samples] → The small-sample mark is a floor, not proof, and the view says results don't predict.
- [The entry can differ a little from the alert's price] → Accepted, for the split protection above.
- [A slow backfill] → Accepted. Newest days come first, and those matter most.
