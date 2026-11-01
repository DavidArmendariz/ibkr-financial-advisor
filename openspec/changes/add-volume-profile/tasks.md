# Tasks

## 1. Backend

- [x] 1.1 Add `backend/signals/volume_profile.py` with bucket sizing, even spreading, POC, and value area; verify in new `tests/test_volume_profile.py` with hand-worked bars, a tie, a one-bucket session, and zero volume, and against the prototype's Oct 30 result
- [x] 1.2 Add current and previous profiles to `SignalPipeline`, counting regular-hours bars only, including during warmup; verify with tests for pre-market and after-hours bars, a session change, an early close, and that yesterday's levels survive after the chart history drops its bars
- [x] 1.3 Add `volume_profile` to `live()` in `service.py`, cached until a bar completes; verify with a test and a request to the running backend

## 2. Chart

- [x] 2.1 Add types and `src/components/signals/volumeProfilePrimitive.ts`, and attach it to the candle series; verify `npx tsc --noEmit -p .` passes, and in the browser with real data that bars line up with the prices of known levels
- [x] 2.2 Add today's and yesterday's level lines; verify in the browser that they match the backend's values
- [x] 2.3 Add the legend toggle with `localStorage` in `try/catch`; verify with Playwright that it hides bars and lines, and stays off after reload
- [x] 2.4 Update the README's Signals features, including that levels are estimates; verify the wording against the view

## 3. Integration checks

- [x] 3.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 3.2 Look at the Signals view in a browser at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths, with the sidebar hidden, and after zooming, confirming the RSI pane stays aligned
- [x] 3.3 Confirm `.env` and `ibkr_advisor.db` are unchanged after testing

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
