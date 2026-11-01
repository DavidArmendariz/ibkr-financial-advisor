# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

The app already fetches public data in the backend with `httpx` for the TRM rate, with a refresh task, a retry interval, and errors shown on its card. API keys live in `.env`, and the renderer only sees "set / hint". `signal-notifications.cjs` listens to the signals WebSocket in Electron's main process, and clicking opens the Signals view through `onClick`.

Findings from probes:

| Source | Result |
|---|---|
| IBKR Wall Street Horizon | Refused on this account: error 10276, "News feed is not allowed" |
| FRED API | Reachable; needs a free key. Data not yet confirmed |
| Federal Reserve FOMC page | Reachable; lists meetings through 2027 |
| BLS calendar file | Refuses automated requests (403) |
| BEA schedule | Reachable; not needed if FRED covers it |
| CNN-style scraping | Not used |

## Goals / Non-Goals

**Goals:**

- A dependable list of upcoming SOXL-relevant events, with warnings before them.

**Non-Goals:**

- Muting or marking signals around events. That can follow once the calendar is trusted.
- Consensus estimates or actual results.
- Non-US events, or a full market calendar.
- Earnings for every SOXL holding.

## Decisions

### FRED for releases, the Fed's page for FOMC

FRED release dates are official, and need a free key. FOMC dates come from parsing the Fed's calendar page, which FRED doesn't cover as a release. The parser fails loudly on an unexpected page rather than silently showing nothing.

- *Alternative: a commercial economic calendar.* Lost because Finnhub's economic calendar is reported as premium, and official sources are enough.
- *Alternative: BLS's calendar file.* Lost because BLS refuses automated requests, and working around that isn't appropriate.
- *Alternative: a list maintained by hand.* Lost because dates shift and would go stale.

### Finnhub for earnings, verified first

Finnhub's earnings calendar is the first choice, using a free key. Its free-tier access is unconfirmed, so the first task checks it with a real key. If it isn't included, implementation pauses to try Financial Modeling Prep or ask the user.

- *Alternative: IBKR's Wall Street Horizon data.* Lost because the account is refused, and it would need a subscription.
- *Alternative: a watchlist of dates typed by hand.* Lost because earnings dates move, though it stays a fallback.

### Fixed release times in code

FRED gives dates, so a table maps each release to its usual ET time, such as 08:30 for CPI and the jobs report, and 14:00 for FOMC.

- *Alternative: leave times unknown.* Lost because the 30-minute alert is the most useful one.

### Save events, then read from SQLite

`CalendarEvent` holds events keyed by source and source ID, replaced per source on a successful refresh. The API reads from it, so a failed refresh loses nothing. `CalendarAlert` records each fired alert by event and kind, which makes alerts fire once.

- *Alternative: keep events in memory like TRM.* Lost because alert dedupe and offline use need to survive restarts.

### Alerts run in the backend and reuse the WebSocket

A loop checks once a minute and broadcasts a `calendar` event through the existing signals socket, so alerts arrive with the window closed. `signal-notifications.cjs` shows them, and clicking opens Calendar. Only high-importance events and watchlist earnings alert, to avoid noise.

- *Alternative: schedule in Electron.* Lost because the backend owns events and the record of what fired.
- *Alternative: a second WebSocket.* Lost because one connection already does this job.

### A new `backend/calendar_events` package

Sources, storage, and the loop stay together, with a name that doesn't shadow Python's `calendar` module, which `ibkr_service` imports.

- *Alternative: put it under `backend/macro`.* Lost because it has no IBKR dependency, and it's its own capability.

### Sidebar item between Macro and Settings

- *Alternative: a card in Macro.* Lost because a 30-day list needs its own space. The Macro spec's sidebar position still holds.

## IBKR dependencies

None. The calendar makes no IBKR requests, needs no market data permissions, and is unaffected by pacing or market hours. It's still behind the app's connection lock screen.

## Risks / Trade-offs

- [Finnhub's free plan refuses most foreign listings, such as `005930.KS`] → A refused symbol only affects itself, and the view names it. Samsung works through its US over-the-counter ticker, `SSNLF`.
- [The Fed page's layout can change] → The parser reports an error, saved events stay, and a test uses a saved page.
- [FRED release IDs or dates may not match expectations] → Verified with a real key before relying on them.
- [Rescheduled releases] → Each refresh replaces that source's events, and alert records follow the event's ID and time, so a moved event can alert at its new time.
- [Alerts need the app running] → Same as signals, and the spec covers missed alerts.
- [Do Not Disturb hides alerts] → As found earlier; Electron or DeltaAdvisor must be allowed.
- [Sending a key to the wrong place] → Keys go only to their own provider's HTTPS endpoint, and errors never include them.
