# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`SignalPipeline.on_bar` handles every warmup and live bar. `history` keeps 1,500 bars for the chart, which on 1-minute bars with pre-market can drop part of yesterday's regular session by the end of today. `lightweight-charts` 4.2.3 offers `attachPrimitive`, which draws in the chart's own panes, and `createPriceLine`. `SessionCalendar` knows regular hours, including early closes.

A prototype on cached SOXL bars gave these results:

| Session | Bucket | Buckets | POC | Value area |
|---|---:|---:|---:|---|
| Oct 26 | $0.10 | 90 | 90.70 | 87.60–93.20 |
| Oct 28 | $0.25 | 30 | 104.25 | 102.75–106.25 |
| Oct 30 | $0.10 | 140 | 73.40 | 70.20–78.60 |

Across 180 sessions, buckets ranged from 14 to 295, averaging 65.

## Goals / Non-Goals

**Goals:**

- A profile and levels that read as context behind the candles.

**Non-Goals:**

- Alerts on profile levels.
- Tick-accurate data, or profiles over several sessions.
- Profiles on pre-market or after-hours trading.
- Settings for bucket size or value area percentage.
- Backtesting the levels.

## Decisions

### Calculate in the backend, incrementally

`volume_profile.py` holds pure functions, tested with pytest like the other indicators. The pipeline adds each regular-hours bar to the current session's profile, and keeps the previous one.

- *Alternative: calculate in the renderer from chart bars.* Lost because the renderer has no unit tests, and the 1,500-bar limit could cut off yesterday.
- *Alternative: enlarge the chart history.* Lost because it adds cost to every chart message for one feature.

### Spread each bar's volume evenly across its range

Bars have no per-price volume, so each one's volume is split across the buckets from its low to its high.

- *Alternative: put it all at the typical price.* Lost because it creates false spikes on wide bars.
- *Alternative: reconstruct from 5-second bars.* Lost because history doesn't provide it, and live and warmup data would differ.

### Bucket size from price

The bucket is the smallest of $0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1, 2, 5 that's at least 0.1% of the session's first close, fixed for the session.

- *Alternative: a fixed number of buckets.* Lost because bucket edges would shift as the range grows, moving levels around.

### Regular hours only, whatever the VWAP setting

Pre-market prints are thin and would distort the levels. It's also how traders usually quote POC.

- *Alternative: follow `include_premarket`.* Lost because it would change the levels in a way that's easy to miss.

### Bars through a series primitive

A primitive on the candle series draws bars in the chart's pane, using `priceToCoordinate`, so it follows zoom and price scale changes without extra code. Bars extend left from the right edge, up to about 20% of the plot width, and scale to the largest bucket. They use one low-opacity neutral, the POC bucket and value area slightly stronger.

- *Alternative: a positioned HTML overlay.* Lost because it must be resynced on every scale change.
- *Alternative: a separate side panel.* The user chose bars on the chart.

### Levels as price lines

Today's POC is solid, value area lines are dotted, and yesterday's are fainter and dashed, each titled (POC, VAH, VAL, yPOC, yVAH, yVAL). All use dark labels, with yesterday's dimmer, so an unlabelled line can't be mistaken for today's.

- *Alternative: draw lines in the primitive.* Lost because price lines already provide labels.

### Sent with the `live` update

The `volume_profile` field holds `bars`, the session to draw with its `bucket` and `buckets`, and `today` and `yesterday`, each with `poc`, `value_area_high`, and `value_area_low`. Before the open, `today` is empty and `bars` is yesterday's session. It's rebuilt when a bar completes and cached, so the 5-second `live` messages stay cheap.

- *Alternative: a separate event.* Lost because `live` already reaches the view, and a first load gets it in the same snapshot.

### Toggle in the legend, stored in `localStorage`

It's a per-viewer convenience, like the sidebar's collapsed state, wrapped in `try/catch`.

- *Alternative: a saved setting in `.env`.* Lost because nothing in the backend depends on it.

## IBKR dependencies

None change. The profile uses bars the stream already delivers, so pacing is unaffected. Warmup covers yesterday's session, and early closes follow the IBKR trading hours in `SessionCalendar`. Volume comes from the same subscription as bars.

## Risks / Trade-offs

- [Levels are estimates] → The spec and README say volume is spread across each bar's range.
- [A big-range bar flattens its volume] → Accepted, as it's the honest reading of what bars show.
- [Too many lines on the chart] → Yesterday's are muted with dim labels, and the toggle hides everything.
- [Bars cover candles at the right edge] → Low opacity, and the 20% limit. After a zoom, the latest candles can sit under them, so the toggle helps.
- [Levels invite over-reading] → They're context only, with no backtested edge.
