# Tasks

## 1. Backend

- [x] 1.1 Add the volume-weighted standard deviation to `SessionVWAP` and `vwap_std` to `IndicatorValues` and `IndicatorSet`, and update tests that list indicator keys; verify with tests in `tests/test_indicators.py` against a hand-worked example, and that it restarts each session
- [x] 1.2 Add `trigger_vwap_band_enabled` (default on) and `vwap_band_std` (default 2, above 0, up to 5) to `SignalSettings`, outside `pipeline_key()`; verify with tests for the defaults, the range, and an unchanged `pipeline_key()`
- [x] 1.3 Change trigger checks to receive the settings, and add `VWAP_BAND_ABOVE` and `VWAP_BAND_BELOW` to `TRIGGERS`, both using one switch; verify with tests in each direction for a cross, staying beyond, a re-cross, zero spread, a new session, a changed N, separate cooldowns, and independence from the other triggers
- [x] 1.4 Update the existing pipeline tests that assume three triggers; verify `uv run pytest` passes

## 2. Renderer and docs

- [x] 2.1 Add the settings to `src/types/index.ts` and a VWAP band checkbox and standard deviations field to the Technical triggers group in `SignalSettingsForm.tsx`; verify `npx tsc --noEmit -p .` passes, and with Playwright and mocked saves that the defaults show, a change persists after reload, and the all-off note counts this trigger
- [x] 2.2 Add chart markers in `SignalChart.tsx`, with a down arrow above the bar for the below direction, and VWAP band above and below filters in `src/pages/SignalHistory.tsx`; verify with mocked signals in Playwright
- [x] 2.3 Update the README's Signals features, alert counts, and `SIGNALS_*` table; verify the documented defaults match `SignalSettings`

## 3. Integration checks

- [x] 3.1 Run the real pipeline over the cached 180 sessions with default settings, and verify about 1.1 above and 1.0 below alerts per session, matching the prototype
- [x] 3.2 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 3.3 Look at the Signals settings and Signal History in a browser at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths
- [x] 3.4 Confirm `.env` and `ibkr_advisor.db` are unchanged after testing

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
