# Tasks

## 1. Backend triggers and settings

- [x] 1.1 Add `trigger_volume_enabled` (default on), `trigger_ema_enabled` (default on), and `trigger_vwap_enabled` (default off) to `SignalSettings`, outside `pipeline_key()`; verify with `tests/test_rules.py` cases for the defaults, that all-off saves, and that a switch change leaves `pipeline_key()` the same
- [x] 1.2 Replace `is_long_entry` and `LONG_ENTRY` in `backend/signals/rules.py` with a `TRIGGERS` list of `VOLUME_SPIKE`, `EMA_CROSS`, and `VWAP_CROSS` checks with their categories; verify with tests that each fires alone and doesn't depend on the others, including the spec's cross below VWAP, EMA already above, and low volume scenarios
- [x] 1.3 Update `SignalPipeline.on_bar` to evaluate the triggers that are on and apply blackouts and a per-trigger cooldown; update existing pipeline tests that used `LONG_ENTRY`; verify with tests for two signals on one bar, cooldowns not blocking each other, all triggers off, and a switch through `apply_settings` affecting the next bar
- [x] 1.4 Add `category` to `Candidate`, its snapshot, the signal record in `service.py`, and the stored payload; verify with a test that a saved record keeps its category through `_load_history`, and that `uv run pytest` passes

## 2. Notifications and Signals view

- [x] 2.1 Show the category in `describe()` in `electron/signal-notifications.cjs`, tolerating records without one; verify by calling `describe()` from `node` with volume, EMA, and category-less records
- [x] 2.2 Add the three settings and `category` to `src/types/index.ts`, and group the switches into Volume and Technical in `SignalSettingsForm.tsx`, with the relative volume threshold in the Volume group; verify `npx tsc --noEmit -p .` passes, and with Playwright that defaults show, a change persists after reload, and all-off saves with a note that alerts are off
- [x] 2.3 Show trigger and category in `SignalTable.tsx`, and distinguish category in `SignalChart.tsx` markers; verify with mocked signals in Playwright
- [x] 2.4 Update the README's Signals features and `SIGNALS_*` table with the triggers, categories, and defaults, and update the Signals section of `CLAUDE.md` if it describes the old rule; verify the documented defaults match `SignalSettings`

## 3. Integration checks

- [x] 3.1 Run the real pipeline over the cached 180 sessions with default settings, and verify about 34 alerts per session, split by trigger
- [x] 3.2 Backtest EMA cross and VWAP cross separately in the scratchpad with the earlier fixed exits, costs, and random baseline, and report the table to the user; volume alerts have no direction, so report only their counts
- [x] 3.3 Run `uv run python -m backend.signals.replay --date 2026-10-28` and verify it lists each signal with its trigger
- [x] 3.4 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 3.5 Look at the Signals settings, table, and chart in a browser at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths

## Workflow follow-up

- The `signal-alerts` Purpose mentions long entry setups, so update it directly in the main spec at archive time.
- Archive the change with `/opsx:archive` after review.
