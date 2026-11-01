# Tasks

## 1. Backend

- [x] 1.1 Add a Wilder `RSI` class to `backend/signals/indicators.py`, and `rsi` to `IndicatorValues` and `IndicatorSet`, leaving `ready()` unchanged; verify in `tests/test_indicators.py` against a hand-worked example and a `pandas` comparison, plus the no-losses and warmup cases
- [x] 1.2 Add `trigger_rsi_enabled` (default on), `rsi_upper` (75), `rsi_lower` (25), and `rsi_period` (14) to `SignalSettings`, with `rsi_period` in `pipeline_key()` and `warmup_bars()`, and reject a lower level at or above the upper; verify with tests for the defaults, the rejection, and which settings change `pipeline_key()`
- [x] 1.3 Add `RSI_ABOVE` and `RSI_BELOW` to `TRIGGERS` on one switch; verify with tests in each direction for a cross, staying beyond, a re-cross, a new session, changed levels, separate cooldowns, and independence from the other triggers
- [x] 1.4 Update existing pipeline tests that assume the current triggers, and add a test that both RSI types are judged in both directions; verify `uv run pytest` passes

## 2. Renderer and docs

- [x] 2.1 Add RSI to `describe()` in `electron/signal-notifications.cjs`, tolerating signals without it; verify by calling `describe()` from `node` with and without RSI
- [x] 2.2 Add the settings and `rsi` to `src/types/index.ts`, an RSI checkbox and fields to the Technical triggers group in `SignalSettingsForm.tsx`, an RSI tile in `LiveValues.tsx`, and an RSI column in `SignalTable.tsx`; verify `npx tsc --noEmit -p .` passes, and with Playwright and mocked saves that the defaults show, a change persists after reload, and the all-off note counts this trigger
- [x] 2.3 Add chart markers in `SignalChart.tsx` and RSI above and below filters in `src/pages/SignalHistory.tsx`; verify with mocked signals in Playwright
- [x] 2.4 Update the README's Signals features, alert counts, and `SIGNALS_*` table; verify the documented defaults match `SignalSettings`

## 3. Integration checks

- [x] 3.1 Run the real pipeline over the cached 180 sessions with default settings, and verify about 1.5 above and 1.6 below alerts per session, matching the prototype
- [x] 3.2 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 3.3 Look at the Signals settings, live values, and Signal History in a browser at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths
- [x] 3.4 Confirm `.env` and `ibkr_advisor.db` are unchanged after testing

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
