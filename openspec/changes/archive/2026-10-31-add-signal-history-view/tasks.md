# Tasks

## 1. Backend

- [x] 1.1 Add `SignalService.history_page()` with a time-and-id cursor and an optional trigger filter, sharing row conversion with `_load_history` and leaving out `bars`; verify in new `tests/test_signal_history.py`, using a temporary database, for newest-first order, a page boundary between signals with the same time, the end of the list, and filtering
- [x] 1.2 Add `GET /api/signals/history` to `backend/routers/signals.py` with `limit` capped at 100, `type`, and `before`, returning 422 for an unknown type or bad cursor; verify with tests and a request to the running dev backend
- [x] 1.3 Document the endpoint in the README's API reference; verify `uv run pytest` passes

## 2. Renderer

- [x] 2.1 Add the history types, `getSignalHistory` in `src/lib/api.ts`, and `'signal-history'` to `AppTab`, and make `bars` unnecessary for `SignalTable`; verify `npx tsc --noEmit -p .` passes
- [x] 2.2 Add `src/hooks/useSignalHistory.ts` with loading, Load older, a filter that resets the list, and a 15 second poll that merges new rows by id; verify with Playwright and mocked responses that a new row joins the top while older rows stay, and that requests stop when leaving the view
- [x] 2.3 Add `src/pages/SignalHistory.tsx` with the trigger filter, table, Load older, and empty and backend-unreachable states; verify each state with Playwright and mocked responses
- [x] 2.4 Add Signal History below Signals in `src/components/Sidebar.tsx` and render it in `src/components/Layout.tsx`; verify in the browser that it opens and shows as selected
- [x] 2.5 Add the view to the README's features and project tree; verify the wording against the view

## 3. Integration checks

- [x] 3.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 3.2 Look at the view in a browser at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths and with the sidebar hidden, and verify the real empty state, since no signals are recorded yet
- [x] 3.3 Confirm `ibkr_advisor.db` has no test rows after testing

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
