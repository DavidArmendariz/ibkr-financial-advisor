# Proposal

## Why

SOXL reacts sharply to Fed decisions, inflation and jobs data, and chip earnings, and the app gives no warning of them. Signals fired into those moments are more likely to be noise, so the user wants to see what's coming and be warned before it happens.

## What Changes

- Add a **Calendar** item to the sidebar, below Macro, listing upcoming events for the next 30 days, each with its date, time in ET, category, and importance.
- **Economic events:** FOMC decisions, CPI, PPI, the jobs report, GDP, PCE, and retail sales.
- **Earnings:** a chip watchlist editable in settings, defaulting to NVDA, TSM, AVGO, AMD, ASML, MU, INTC, QCOM, AMAT, and LRCX, marked before the open or after the close when known.
- A notification the evening before each event, and 30 minutes before when the time is known, each with an on/off switch. Each alert fires once, including across restarts.
- API key fields in Settings for FRED and Finnhub, both free to sign up for. If one is missing, the view says what's needed and shows the rest.
- Events are saved locally, so the view works when a source is down.

## Capabilities

### New Capabilities

- `event-calendar`: upcoming economic and earnings events, their sources, alerts before them, and the settings for them.

### Modified Capabilities

None. Signals, alerts, and the LLM filter don't change, and the existing sidebar requirements still hold.

## Impact

- **IBKR access:** none. A probe found IBKR's Wall Street Horizon calendar is refused on this account (error 10276), so the calendar doesn't use IBKR.
- **Order handling:** not touched.
- **API keys:** two new keys, stored in `.env` with owner-only permissions. The renderer only sees "set / …abcd hint", and all requests happen in the backend.
- **Data leaving the machine:** requests go to FRED, the Federal Reserve site, and Finnhub, with the API keys and public release IDs or date ranges. No positions, orders, or account data are sent.
- **Code:** new `backend/calendar_events/` package, new `backend/routers/calendar.py`, `backend/database.py`, `backend/main.py`, `electron/signal-notifications.cjs`, `electron/main.cjs`, new `src/pages/Calendar.tsx`, new `src/hooks/useCalendar.ts`, `src/pages/Settings.tsx`, `src/components/Sidebar.tsx`, `src/components/Layout.tsx`, `src/lib/api.ts`, `src/types/index.ts`, `README.md`, new backend tests.
- **Database:** adds `CalendarEvent` and `CalendarAlert` tables, created automatically.
- **Settings:** adds `CALENDAR_*` keys to `.env`.
