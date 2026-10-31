# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`is_long_entry` in `backend/signals/rules.py` ANDs a VWAP cross, fast EMA above slow EMA, and relative volume above the threshold, and `SignalPipeline.on_bar` emits at most one `LONG_ENTRY` candidate per bar. Cooldown is already keyed by signal type in `last_fired`, and `on_bar` already returns a list. The signal type flows as a plain string to the database, table, replay, and notification title.

No `LONG_ENTRY` rows exist in the local database, so nothing needs migrating.

Measured on 180 sessions of cached 1-minute bars, including blackouts and a 5-minute cooldown, in alerts per session: relative volume above 1.5× 26.3, above 3× 4.1, EMA cross 8.0, VWAP cross 4.4.

## Goals / Non-Goals

**Goals:**

- Each trigger fires, switches, and notifies independently.
- Triggers are grouped by category, so more can join either one later.

**Non-Goals:**

- Trigger combinations, such as requiring volume with a cross. The user explicitly removed these.
- Downward crosses or sell alerts. EMA and VWAP crosses stay upward only.
- Direction on volume alerts.
- A separate threshold, cooldown, or LLM setting per trigger. The existing cooldown applies to each trigger separately, and the volume threshold is the existing setting.
- Choosing a profitable trigger set. The defaults are what the user asked for, not a backtested result.

## Decisions

### One small function per trigger

`rules.py` holds a `TRIGGERS` list, each entry with a type (`VOLUME_SPIKE`, `EMA_CROSS`, `VWAP_CROSS`), a category (`volume` or `technical`), and a check. `on_bar` loops over the triggers that are on and applies the existing cooldown by type. `is_long_entry` and `LONG_ENTRY` go away.

- *Alternative: keep `is_long_entry` with switch arguments.* Lost because independent triggers can each fire on one bar, which one boolean can't express.
- *Alternative: a class per trigger or a plugin registry.* Lost because three short functions don't justify the structure.

### The volume trigger fires on each qualifying bar

It fires when a bar is above the threshold, limited by the cooldown, which is what the user asked for ("we always get a volume alert").

- *Alternative: fire only when RVOL rises through the threshold.* Lost because it barely helps, at 24.8 instead of 26.3 alerts per session, and it would skip a sustained surge after the cooldown.

### Keep the volume threshold default at 1.5×

The user asked for it to stay configurable and didn't ask to change the default. It already exists as `rvol_threshold`, and the settings form shows it in the Volume group.

- *Alternative: raise the default to 3×.* Offered and not chosen. It would cut volume alerts to about 4 per session, so the user can set it if alerts are too frequent.

### Cooldown is per trigger

Each trigger keeps its own cooldown clock, as the spec's "same type" wording already says, so a volume alert doesn't suppress an EMA alert on the same bar.

- *Alternative: one shared cooldown.* Lost because triggers wouldn't be independent.

### Category comes with the signal

Each candidate carries its category, stored in the signal payload and sent to the renderer and LLM snapshot. The renderer doesn't need to know the mapping.

- *Alternative: derive it in the renderer from the type.* Lost because the mapping would live in two places.

### Three boolean settings, applied without a rebuild

`trigger_volume_enabled`, `trigger_ema_enabled`, and `trigger_vwap_enabled` join `SignalSettings` as `SIGNALS_*` keys and stay out of `pipeline_key()`, since no indicator state depends on them. `apply_settings` already passes new settings to the running pipeline.

- *Alternative: one comma-separated list.* Lost because it needs its own parsing, while booleans already fit the form and `.env`.

### Allow all triggers off

- *Alternative: reject the save.* Lost because "no alerts for now" is a reasonable choice now that triggers are independent. The settings form shows that alerts are off.

## IBKR dependencies

None change. Real-time bars still need the Network B subscription, and alerts still depend on the stream running during market hours. Pacing is unaffected. Relative volume is a 20-bar comparison, so volume alerts are likely to cluster around the open and news, when volume jumps.

## Risks / Trade-offs

- [About 34 notifications per session by default, or roughly one every 11 minutes] → Stated in the proposal. The threshold, cooldown, and switches all reduce it, and the final summary repeats the numbers.
- [Volume alerts have no direction, so they can't be read as a buy signal] → The notification names the trigger, and the Volume category keeps it apart from technical triggers.
- [The default triggers have no backtested edge] → Stated in the proposal. The tasks backtest EMA and VWAP crosses separately and report the result.
- [With the LLM filter on, cost rises with alert count] → It stays off by default, and the proposal notes it.
- [The Signals history holds only the latest 50, which about 1.5 sessions fill at this rate] → Accepted. The database keeps every signal.
- [The chart's signal markers crowd at this frequency] → Markers differ by category, and this is checked in the browser.
