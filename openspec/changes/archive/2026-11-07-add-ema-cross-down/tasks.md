# Tasks

## 1. Trigger

- [x] 1.1 Add `EMA_CROSS_DOWN`, its test with a `crosses_below` helper, the `trigger_ema_down_enabled` setting off by default, and its `TRIGGERS` entry
- [x] 1.2 Test a bearish cross, no cross while staying below, an upward cross raising only `EMA_CROSS`, a new session, the default off, and that replaying the cached sessions with it off gives the same signals as before

## 2. Analysis

- [x] 2.1 Judge `EMA_CROSS_DOWN` as a short in `directions_for`, and give short figures in the post-mortem and its panel when short is the only direction; test it

## 3. View

- [x] 3.1 Add the setting switch, label the existing switch as the upward cross, include the new one in the all-off check, and add the downward chart marker and the Signal History filter
- [x] 3.2 Update the README triggers and settings table

## 4. Verification

- [x] 4.1 Verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 4.2 Look at the settings, a downward marker, and the filter in a browser, and replay a session with it on to see signals fire

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
