# Tasks

## 1. Stop requesting denied bars

- [x] 1.1 In `backend/macro/service.py`, add a `bars_denied` flag to `Slot`. Set it in `_on_error` for code 162 when the message contains "No market data permissions", skip `_refresh_bars` in `_tick_slot` while it's set, and clear it in `_on_disconnected`. Verify with tests in `tests/test_macro.py`: a permission denial stops further bar requests on later ticks, another 162 message (e.g. "HMDS query returned no data") doesn't, and a disconnect makes the next tick request bars again
- [x] 1.2 Check that the existing `test_refused_history_shows_when_card_has_no_value` still passes unchanged: the card still shows the error

## 2. Verification

- [x] 2.1 Run `uv run pytest`, `npx tsc --noEmit -p .` and `npx vite build`; all pass
- [x] 2.2 With the dev backend connected to paper, open the Macro view in the browser at http://localhost:5273. Check that the Dow Jones card still shows its value or the 162 error, and that the backend log shows the CME IND error once, not again after 5+ minutes
  - The first live check logged it twice, from the same refresh: the daily request went out right after the denial. `_refresh_bars` now stops after the first request when it's denied, and the test denies during the request. After that the log shows it once, and the Dow Jones card still shows the 162 error.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, so the macro-indicators spec gets the new scenarios.
