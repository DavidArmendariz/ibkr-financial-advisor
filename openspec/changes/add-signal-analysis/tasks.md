# Tasks

## 1. Analysis logic

- [x] 1.1 Add `backend/signals/analysis.py` with bar splitting at the signal's time and outcome calculations; verify in new `tests/test_signal_analysis.py` with hand-worked bars for the boundary bar, each horizon, a horizon after the close, largest gain and loss, and returning to the start level
- [x] 1.2 Add direction by trigger and the pre-mortem and post-mortem prompts and reply validation; verify with tests that a pre-mortem request holds no later bars, that two pre-mortems on different dates send identical data, that no account fields appear, and that invalid replies are rejected
- [x] 1.3 Extend `complete()` with `max_tokens` and an optional `schema`, keeping the filter's defaults; verify the existing LLM filter tests pass unchanged
- [x] 1.4 Add an end time to `get_historical_bars`; verify with a test that existing callers behave as before

## 2. Backend API and storage

- [x] 2.1 Add the `SignalAnalysis` table and save and load functions; verify with a temporary database that a success replaces the old result, a failure keeps it, and results survive a reload
- [x] 2.2 Add `POST /api/signals/{id}/analysis/{kind}` with the too-recent check, in-flight 409, and errors for no provider, no connection, no bars, timeout, and invalid replies; verify each with a fake provider and fake bars, confirming refused requests make no provider call
- [x] 2.3 Include saved analyses in `GET /api/signals/history`; verify with a test and that `uv run pytest` passes
- [x] 2.4 Document the endpoint, provider data, and buttons in the README; verify the wording against the code

## 3. Renderer

- [x] 3.1 Add types and `runSignalAnalysis` with a 90 second timeout; verify `npx tsc --noEmit -p .` passes
- [x] 3.2 Add the optional `renderDetails` to `SignalTable`, keeping the Signals view unchanged; verify in the browser that the Signals view looks the same
- [x] 3.3 Add `SignalAnalysisPanel` and the buttons to Signal History, with running, result, hindsight, rerun, and error states; verify each state with Playwright and mocked responses, and that browsing still works during a run

## 4. Integration checks

- [x] 4.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 4.2 With the user's agreement, because it calls the paid provider, run one real pre-mortem and post-mortem on a real or clearly marked test signal against recent bars, and show the results
- [x] 4.3 Look at Signal History in a browser at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths
- [x] 4.4 Confirm no test rows from automated checks remain in `ibkr_advisor.db`, apart from any the user chose to keep

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
