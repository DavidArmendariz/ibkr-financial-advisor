# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`SessionVWAP` keeps running totals of price × volume and volume, and restarts at each session anchor. Triggers live in `TRIGGERS` in `rules.py`, each receiving the previous close, previous values, close, current values, and the relative volume threshold. The pipeline, cooldowns, notifications, history, and API all handle a new trigger type without changes, apart from the trigger list and filter labels.

Measured on 180 sessions of cached 1-minute bars with a 5-minute cooldown, outside blackouts, per session:

| N | Crosses above | Crosses below | Total | Bars above the upper band |
|---:|---:|---:|---:|---:|
| 1 | 4.8 | 4.1 | 8.9 | 98.7 |
| 1.5 | 3.3 | 2.8 | 6.1 | 37.1 |
| 2 | 1.1 | 1.0 | 2.1 | 7.3 |
| 2.5 | 0.2 | 0.2 | 0.4 | 0.6 |
| 3 | 0.0 | 0.1 | 0.1 | 0.1 |

## Goals / Non-Goals

**Goals:**

- A separate alert when price crosses a user-set distance above or below VWAP.

**Non-Goals:**

- Separate N values or switches for each direction.
- Drawing the band on the chart, or showing it in the live values.
- Saying whether the move is a buy or a stretched level to fade. The alert states the fact only.

## Decisions

### Volume-weighted standard deviation around VWAP

The standard deviation is `sqrt(Σ(volume × typical²) / Σvolume − VWAP²)`, kept with one more running total in `SessionVWAP`. This is what charting platforms call VWAP bands, and it restarts with VWAP.

- *Alternative: rolling standard deviation of the distance from VWAP.* Lost because it needs its own window setting and would differ from bands traders know.
- *Alternative: reuse Bollinger's width.* Lost because it measures spread around a moving average rather than VWAP.

### Two signal types behind one switch

`VWAP_BAND_ABOVE` and `VWAP_BAND_BELOW` are separate entries in `TRIGGERS`, sharing `trigger_vwap_band_enabled` and `vwap_band_std`. Each therefore gets its own notification, cooldown, and history filter with no special handling.

- *Alternative: one `VWAP_BAND` type with a direction field.* Lost because cooldown and filters key on type, so a direction field would need special cases, and an above alert could block a below alert.
- *Alternative: two switches.* Lost because the user described one alert with two directions, and it adds a setting with no clear use.

### Fire on the cross, not on every bar beyond

Each direction fires when the previous close was inside its band and this close is beyond it, as with the other technical triggers.

- *Alternative: fire on every bar beyond the band.* Lost because the alert would repeat for as long as price stays stretched, up to the cooldown limit. It would be noisier and add no new information.

### Store the standard deviation, not the band

`IndicatorValues` gains `vwap_std`, and the trigger computes the band from N. N doesn't affect indicator state, so it stays out of `pipeline_key()` and applies live.

- *Alternative: band values in the indicators.* Lost because changing N would need an indicator rebuild.

### Triggers receive the settings

The `fires` functions take `SignalSettings` in place of `rvol_threshold`, because this trigger needs a different value, and the existing tests update to match.

- *Alternative: add another positional argument.* Lost because every trigger would carry parameters it doesn't use.

### Default N of 2, trigger on, range above 0 to 5

At 2, it fires about once a session in each direction, which suits an unusual-move alert. The user asked for the notification, so it starts on.

- *Alternative: default of 1.* Lost because about 8.9 alerts per session isn't unusual, and price spends a lot of time beyond that band.
- *Alternative: off by default.* Lost because the user asked for this alert.

## IBKR dependencies

None change. The trigger uses the same real-time bars. With pre-market included, the standard deviation starts at 04:00 ET, so a large pre-market move widens the band for the rest of the session. Blackouts and market hours apply as for other triggers.

## Risks / Trade-offs

- [The band widens through the day, since the standard deviation is cumulative] → This matches standard VWAP bands, and it's why alerts are rarer late in a trending session.
- [Early in a session the spread is small, so the first minutes can cross easily] → The open blackout covers regular hours, and with pre-market included the session has started hours earlier.
- [A below alert on a long-only setup could read as a sell signal] → The alert only states the level, and the chart shows it as a down arrow, not an order or a recommendation.
- [Existing signals have no `vwap_std`] → The field is optional in the snapshot, and nothing reads it from stored records.
- [The trigger has no backtested edge] → It's an alert, not a strategy. The summary states that, and the tasks report its count.
