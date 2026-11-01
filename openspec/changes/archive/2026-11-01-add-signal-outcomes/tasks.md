# Tasks

## 1. Measurement

- [x] 1.1 Add `SignalOutcome` and `OutcomeBaseline` tables to `backend/database.py`
- [x] 1.2 Add `backend/signals/outcomes.py` with pure functions for one signal's figures and a day's baseline, reusing `_closes_at` and `_percent` from `analysis.py`; test the 5/15/30 moves, largest moves, the regular close limit, a half-day, a missing entry bar, and a day's baseline
- [x] 1.3 Add a results function for per-trigger and baseline figures; test sample sizes per horizon, median, share up, and that not-available signals are left out

## 2. Background pass

- [x] 2.1 Add a 5-minute task to `SignalService`, started and stopped with the service, that measures one ET day per pass, newest first, using `get_historical_bars`
- [x] 2.2 Test with mocked bars: signals under 30 minutes old wait, saved figures aren't requested again, disconnected pauses without marking anything, errors stay pending, and a past day with no bars is marked not available
- [x] 2.3 Add a test that a pass makes no provider call, doesn't change `SignalEvent` rows, and calls no order function

## 3. API and view

- [x] 3.1 Add `GET /api/signals/outcomes` and an `outcome` field on history records, with tests
- [x] 3.2 Add types and an API call, and a results component on the Signal History page with the baseline row, small-sample marks, pending count, empty state, and the note that results don't predict
- [x] 3.3 Show outcome figures, pending, or not available in each signal's details

## 4. Docs and verification

- [x] 4.1 Update the README and add `signal-outcomes` to the capability list in `CLAUDE.md`
- [x] 4.2 Verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 4.3 Replay the cached sessions and confirm signals don't change
- [x] 4.4 Run a real backfill against the paper connection, compare a few signals by hand against IBKR bars, and look at Signal History in a browser

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
