# Tasks

## 1. Data model

- [x] 1.1 Add `MoneySupplyObservation(series_id, month, value)` with a composite primary key and `MoneySupplyMeta(series_id, last_updated, next_release, fetched_at, error)` to `backend/database.py`. Verify that `uv run pytest` still passes and that both tables are created on a fresh DB.

## 2. FRED fetch and calculations

- [x] 2.1 Create `backend/money_supply/sources.py`. It fetches M2SL observations (dropping `"."`), the series' `last_updated`, and the next H.6 release date (release 21; best-effort). It has its own `_get` that reports only the label plus the exception type or HTTP status. Add `tests/test_money_supply.py`, with parsing tests on canned FRED JSON, a missing-value test, and a test that error text never contains the key or the URL.
- [x] 2.2 Create `backend/money_supply/calc.py` with the YoY series (None when there's no observation 12 months earlier) and the latest reading (MoM and YoY changes, in dollars and percent). Test 1959 rows having no YoY, a negative-growth month, and the latest-reading numbers on a small fixture.

## 3. Service and API

- [x] 3.1 Create `backend/money_supply/service.py` with `MoneySupplyService`. It runs a 1-minute loop, refreshes every 6 hours after success and every hour after failure, refreshes immediately when the FRED key changes, and reports `no_key` with no fetch when there's no key. Each refresh replaces the series' rows in one transaction and keeps saved rows on failure. Test with an injected fetcher and clock: due and retry timing, a key change triggering a refresh, a failure keeping the old rows and recording the error, and state loading from the DB after a fresh service instance (restart).
- [x] 3.2 Add `backend/routers/money_supply.py` (`GET /api/money-supply`, returning the state shape from design D6), register it in `backend/main.py`, and start and stop the service in the lifespan. Test the response with a TestClient: `no_key`, `ok` with data, and `error` with saved data, and check that the FRED key never appears in the body.
- [x] 3.3 Add `GET /api/money-supply` to the API reference in README.md, and note in the Calendar key's Settings description that the key also powers M2. Check that the README renders.

## 4. Renderer

- [x] 4.1 Add `'money-supply'` to `AppTab` in `src/types/index.ts`, plus the response types, and a `getMoneySupply` call in `src/lib/api.ts`. Verify with `npx tsc --noEmit -p .`.
- [x] 4.2 Create `src/hooks/useMoneySupply.ts`. It fetches on mount and polls every 60 s while the view is open, and it holds the range (`5y | 10y | 25y | all`, default `10y`), persisted in `localStorage` under `money-supply:range` with try/catch. Verify with tsc.
- [x] 4.3 Create `src/components/money-supply/LatestReading.tsx`: the value in trillions, the month, MoM and YoY in dollars and percent, last updated, the next release (left out when null), and the error and last-update line when status is `error`. Verify with tsc.
- [x] 4.4 Create `src/components/money-supply/M2Charts.tsx`: two stacked Recharts panels with a shared `syncId`, a level line, and YoY growth split at zero, with a zero reference line and a tooltip showing month, level and YoY. Load the dataviz skill first for palette and marks. Verify with tsc.
- [x] 4.5 Create `src/components/money-supply/M2Explainer.tsx` with the sections listed in design D9, including that M2 gives context and isn't a timing signal. Verify the text renders.
- [x] 4.6 Create `src/pages/MoneySupply.tsx`, which composes the reading, the range selector, the charts and the explainer. In the `no_key` state it shows the key message, a link that opens Settings, and the explainer. Add the Sidebar item directly below Fundamentals (lucide `Landmark` icon) and the Layout case. Verify with tsc and `npx vite build`.

## 5. Verification

- [x] 5.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, `npx vite build` and `npx openspec validate add-m2-money-supply --strict`. All pass.
- [x] 5.2 Do a visual check with Playwright at http://localhost:5273, with screenshots in the scratchpad. The sidebar item sits below Fundamentals and opens the view. With a key: the latest reading, both charts, a synced hover tooltip, and each range button change both charts. The 2023 YoY dips show in the negative color. The explainer is present. Without a key (temporarily unset `CALENDAR_FRED_API_KEY` in the backend's env): the message, the Settings link working, and the explainer still showing.
