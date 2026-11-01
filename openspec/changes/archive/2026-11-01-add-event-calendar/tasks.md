# Tasks

## 1. Verify sources

- [x] 1.1 With the user's free FRED and Finnhub keys, confirm with one-off requests that FRED returns future dates for CPI, PPI, jobs, GDP, PCE, and retail sales, and that Finnhub's free tier returns the chip watchlist's earnings; if either fails, pause and tell the user

## 2. Backend

- [x] 2.1 Add `CalendarEvent` and `CalendarAlert` tables and `CALENDAR_*` settings, with key saving through `save_env_values` and the "set / hint" pattern; verify with tests that keys never appear in API responses
- [x] 2.2 Add `backend/calendar_events/` sources for FRED, the Fed page, and Finnhub, with the release time table; verify with saved sample responses, including an unexpected Fed page, a two-day meeting, and before-open and after-close earnings
- [x] 2.3 Add refresh and storage with per-source errors and last update times; verify with tests that a failed source keeps its events, a missing key only affects its source, and events survive a reload
- [x] 2.4 Add the alert loop and once-only records; verify with tests using fixed times for the evening alert, 30-minute alert, unknown times, restarts, missed alerts, the grace period, a rescheduled event, and each switch
- [x] 2.5 Add `GET /api/calendar` and start and stop the service in `backend/main.py`; verify with tests and a request to the running backend, and that no request uses a real database in tests

## 3. App

- [ ] 3.1 Handle `calendar` events in `electron/signal-notifications.cjs`, with clicks opening Calendar in `electron/main.cjs`; verify `describe` output from `node`, and with a marked test alert that it reaches the screen
- [x] 3.2 Add `src/pages/Calendar.tsx`, `src/hooks/useCalendar.ts`, types, and the API call, with day groups and missing-key, error, and empty states; verify `npx tsc --noEmit -p .` passes, and each state with Playwright and mocked responses
- [x] 3.3 Add the Calendar sidebar item and render it in `Layout.tsx`; verify in the browser that it opens and shows as selected
- [x] 3.4 Add key fields, the watchlist, and alert switches to Settings; verify with Playwright and mocked saves that keys show only a hint
- [x] 3.5 Update the README's features, setup, API reference, and project tree; add the calendar to CLAUDE.md's layout; verify the wording against the code

- [x] 3.6 Show the watchlist as removable chips instead of comma-separated text; verify with Playwright that typing, pasting, removing, duplicates, and saving work

## 4. Integration checks

- [x] 4.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 4.2 Look at the Calendar view with real data at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths, and compare a few dates against the official sources
- [x] 4.3 Confirm no key appears in logs or the renderer's responses, and that test runs leave `ibkr_advisor.db` unchanged

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
