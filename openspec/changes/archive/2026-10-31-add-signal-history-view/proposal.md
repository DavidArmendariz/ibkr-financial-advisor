# Proposal

## Why

The Signals view shows only the latest 50 signals, and at about 34 alerts per session that is under two sessions' worth. Every signal is already saved locally, but there's no way to look further back, which the user needs to judge the new triggers.

## What Changes

- Add a **Signal History** item to the sidebar, directly below Signals, opening a new view.
- List recorded signals newest first, with time, trigger, category, price, indicator values, LLM decision, and whether a notification was shown.
- Filter by trigger: All, Relative volume, EMA cross, or VWAP cross.
- Load older signals on demand, 100 at a time, and refresh the newest signals while the view is open.
- Add `GET /api/signals/history` to read saved signals.
- The Signals view keeps its latest 50 list unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: adds the Signal History view and its sidebar item. Existing requirements don't change.

## Impact

- **IBKR access:** none. The view reads only the local database, so it works while disconnected.
- **Order handling:** not touched. The view is read-only.
- **API keys:** not touched.
- **Data leaving the machine:** none. The new endpoint is served by the local backend.
- **Code:** `backend/routers/signals.py`, `backend/signals/service.py`, `src/lib/api.ts`, `src/types/index.ts`, new `src/hooks/useSignalHistory.ts`, new `src/pages/SignalHistory.tsx`, `src/components/signals/SignalTable.tsx`, `src/components/Sidebar.tsx`, `src/components/Layout.tsx`, `README.md`, new backend tests.
