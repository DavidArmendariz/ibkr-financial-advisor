# Design

## Context

The Calendar already calls FRED (`backend/calendar_events/sources.py`) with `CALENDAR_FRED_API_KEY`, and its error handling never shows the URL. `calendar_events/service.py` refreshes every 6 hours, retries after an hour, and keeps events in SQLite so they survive a restart. M2 needs the same pattern for a single series. Feature views are wired in through the `AppTab` union, `Sidebar.tsx` and `Layout.tsx`, and each feature has its own `hooks/use*.ts`. The app already depends on `recharts` and `lightweight-charts`.

## Goals / Non-Goals

**Goals:**
- One self-contained backend module and one view, following the existing structure of a service, a router and a page.
- Work fully without IBKR.

**Non-Goals:**
- Other monetary series (M1, real M2, the Fed balance sheet, global M2) or overlays against SPY or SOXL. These could come later as additions to this capability.
- Alerts or notifications on M2 releases. The Calendar can take these later as a FRED release.
- Feeding M2 into the AI Advisor or the signal rules.
- A separate M2 key or settings card.

## Decisions

### D1. Series: M2SL (monthly, seasonally adjusted)
`M2SL` is the series people quote, and seasonal adjustment keeps the month-over-month change meaningful. Monthly data from 1959 is about 800 points, so the whole history fits in one request.
- *Alternative: `WM2NS` (weekly, not seasonally adjusted).* It's fresher by a few weeks, but it isn't seasonally adjusted, so week-to-week moves are mostly seasonal noise. It also starts only in 1980. Rejected for the main view.

### D2. Reuse the Calendar's FRED key
The service reads `get_calendar_settings().fred_api_key`. The key stays where the user already entered it, and the M2 view's link sends them to the same Settings card.
- *Alternative: a new `MONEY_SUPPLY_FRED_API_KEY`.* It follows the one-prefix-per-feature rule more strictly, but the user would have to enter the same key twice and keep both copies in sync. Rejected: the key belongs to the FRED account, not to a feature.

### D3. FRED requests and parsing in `backend/money_supply/`
- `GET /fred/series/observations?series_id=M2SL&file_type=json` returns every observation. FRED writes missing values as `"."`, and those are dropped.
- `GET /fred/series?series_id=M2SL` returns `last_updated`.
- `GET /fred/release/dates?release_id=21` lists release dates for the H.6 Money Stock Measures release. The first date after today is the next release. This call is best-effort: if it fails, the view leaves out the next-release field.

The module has its own `_get` helper that reports only the label and the exception type or HTTP status, like `calendar_events.sources._get`. It doesn't import the calendar's helper, so the two features stay independent.
YoY is computed in Python from the saved levels, so pytest covers it.
- *Alternative: ask FRED for `units=pc1` (percent change from a year ago).* Rejected: it takes a second observations request, and it would be a second copy of the data that could fall out of sync after revisions.
- *Alternative: compute YoY in the renderer.* Rejected: the frontend has no unit tests.

### D4. Storage: a `MoneySupplyObservation` table and a metadata row
`MoneySupplyObservation(series_id, month, value)` with a primary key on `(series_id, month)`. Each refresh replaces the series' rows in one transaction. Keying on `series_id` leaves room for other series without a migration. A small `MoneySupplyMeta(series_id, last_updated, next_release, fetched_at, error)` row holds the status. Both tables are created by the existing `create_all`.
- *Alternative: a JSON cache file.* Rejected: everything else the app saves lives in SQLite, and a partial write could corrupt the file.

### D5. Refresh loop and picking up a new key
`MoneySupplyService` follows the calendar's loop. Each minute it checks whether a refresh is due: every 6 hours after a success, every hour after a failure. It also refreshes immediately when the FRED key differs from the one it last used, which covers both a newly added key and a replaced key. That's how "key added without a restart" works, without touching the calendar router. With no key, nothing is fetched and the status is `no_key`.
- *Alternative: have the calendar settings router call `money_supply_service.refresh_now()`.* Rejected: it couples the calendar to this feature. Checking the key costs nothing and takes at most a minute to notice the change.

### D6. API shape
`GET /api/money-supply` returns:
```
{ status: "ok" | "no_key" | "loading" | "error",
  series: "M2SL", units: "Billions of dollars, seasonally adjusted",
  latest: { month, value, mom_change, mom_pct, yoy_change, yoy_pct } | null,
  observations: [{ month: "YYYY-MM-01", value, yoy_pct | null }],
  last_updated, next_release, fetched_at, error }
```
Every observation is sent: around 800 rows, about 30 KB. The renderer slices it by range, so switching ranges needs no request.
- *Alternative: a `?range=` parameter.* Rejected: the payload is small, and slicing on the client makes switching ranges instant.

### D7. Charts: Recharts, two stacked panels sharing the x-axis
- **Level:** a line in the first categorical slot (`#3987e5`), with the y-axis in trillions (for example "$22.4T").
- **YoY growth:** an area or bars split at zero, with positive values in the validated positive color and negative values in the negative slot, plus a zero reference line. The negative color is how the 2023 contraction stands out.

Both panels use one `syncId`, so hovering shows the same month in each. Palette and mark rules come from the dataviz skill.
- *Alternative: lightweight-charts.* Rejected: it's built for time-indexed price series with crosshairs. Monthly macro data with a split-at-zero fill is simpler in Recharts, which other views already use for non-price charts.
- *Alternative: one chart with two y-axes.* Rejected: dual axes invite reading a correlation the scales create, and the dataviz rules advise against them.

### D8. Range selection kept in `localStorage`
The range (`5y | 10y | 25y | all`, default `10y`) is a per-viewer setting. It's stored under `money-supply:range` with try/catch, the same way `useFundamentals` stores the last ticker.

### D9. The explanation is static text in the page
The explanation is written once in `components/money-supply/M2Explainer.tsx`, as sections with headings, always shown below the charts. It covers:
- what M2 is (M1 plus small time deposits under $100k and retail money market funds);
- the May 2020 change that moved savings deposits into M1, without changing M2;
- why it matters: liquidity, inflation with a lag, and asset multiples;
- how to read the level chart (a long-run uptrend is normal; look at the slope) and the YoY chart (the historical norm is about 5–7%; spikes like Feb 2021's ~27% and the 2023 contraction were rare);
- its limits: it lags, it gets revised, its link to inflation is loose, and it's no timing signal.

There's no LLM call.
- *Alternative: an AI-generated summary like Fundamentals has.* Rejected for now: the explanation is general knowledge that doesn't change, and static text costs nothing and can't make things up. An AI comment on the latest reading could come later.

## Risks / Trade-offs

- [FRED rate limit (120 requests/min per key) shared with the Calendar] → M2 makes 3 requests every 6 hours, which is negligible.
- [FRED revises past months] → each refresh replaces all saved rows, so revisions arrive automatically.
- [Release 21 might be renumbered or stop listing future dates] → the next-release date is best-effort and leaves the field out, as the spec allows.
- [The Calendar's key validation (if any) doesn't know about M2] → the same key works for every FRED endpoint, so no change is needed.
- No IBKR data permissions, pacing or market-hours dependency: the feature never touches IBKR.

## Migration Plan

Additive only: two new tables (created on startup), one new router and one new tab. To roll back, revert the commit. The unused tables do no harm.
