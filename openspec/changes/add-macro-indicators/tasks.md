# Tasks

## 1. Backend: indicators and math

- [x] 1.1 Add `backend/macro/indicators.py` with the indicator list (key, label, contract builder for CL/NYMEX and NQ/CME `ContFuture`s and the TNX/CBOE `Index`, unit, value divisor, change mode `pct` or `bp`) and pure helpers for change / percent change / basis points; add `tests/test_macro.py` covering the gain example (72.40 vs 71.90 → +0.50, +0.70%), the yield example (4.31 vs 4.25 → +6 bp) and a missing previous close; verify `uv run pytest tests/test_macro.py` passes
- [x] 1.2 Check TNX's scale against a known 10-year yield with a one-off script using its own client ID (`IBKR_CLIENT_ID` + 60) and set the divisor; verify the converted value matches a published yield for that day to within 1 bp
  - TNX closed at 50.98 on 2026-10-16 → 5.098% (÷10); published closes were 5.082–5.09%. Divisor 10.

## 2. Backend: service and API

- [x] 2.1 Let `ibkr_service.get_historical_bars` take a qualified contract (keeping the `symbol` form for existing callers) and a `use_rth` flag; verify existing callers still work (`uv run pytest`, Dashboard chart loads)
- [x] 2.2 Add `backend/macro/service.py`: on connect, qualify each `ContFuture` to its concrete `Future`, keep `tradingHours`, call `reqMarketDataType(4)` and `reqMktData` per indicator; re-qualify daily and on reconnect and resubscribe when the conId changes; record per-indicator IBKR errors from `errorEvent` and retry refused ones every 5 minutes; refresh 1 D / 5 min sparkline bars and 5 D daily bars (closed-market fallback) every 5 minutes; expose `state()` with value, previous close, change, data type (live / delayed / closed), contract month, last update, sparkline, error and `connected`. Add tests for the rollover switch (new conId → resubscribe) and the closed/live/delayed labelling using a fake ticker; verify `uv run pytest` passes
- [x] 2.3 Add `backend/routers/macro.py` with `GET /api/macro/state`, register it and start/stop the service in the `main.py` lifespan; verify with `curl localhost:8000/api/macro/state` against TWS that all three indicators report values or an IBKR error
- [x] 2.4 Document the endpoint in the README API reference, the needed subscriptions (NYMEX, CME, CBOE indexes; delayed fallback) in the market data section, and add the market-data-type-4 note next to the Gamma line in CLAUDE.md's IBKR gotchas; verify the documented endpoint and fields match the response

## 3. Renderer

- [x] 3.1 Add `'macro'` to `AppTab`, `MacroState`/`MacroIndicator` types, `getMacroState` in `lib/api.ts`, and `hooks/useMacro.ts` polling every 3 s while mounted; verify `npx tsc --noEmit -p .` passes
- [x] 3.2 Add `components/macro/IndicatorCard.tsx` (label, contract month, last value with unit, change and %/bp styled with `pnlClass`, live/delayed/closed badge with last update time, error text, stale marker) and `components/macro/Sparkline.tsx` (SVG line, single series colour from the dataviz palette, follows container width); verify tsc passes
- [x] 3.3 Add `pages/Macro.tsx` (header, not-connected notice, three cards in a responsive grid), the `Globe` Macro entry between Gamma and Settings in `Sidebar.tsx`, and the route in `Layout.tsx`; add a README feature line for the Macro view; verify the view opens from the sidebar in the browser at http://localhost:5273

## 4. Verification

- [x] 4.1 Run `uv run pytest`, `npx tsc --noEmit -p .` and `npx vite build`; all pass
- [x] 4.2 With Playwright against http://localhost:5273 (scripts and screenshots in the scratchpad): open Macro from the sidebar, check the three cards show values, change, a sparkline and a freshness label; check a value update appears without reload; disconnect from Settings and check the not-connected notice and stale markers; check the layout at a narrow window and with the sidebar hidden
  - 2026-10-17 (Saturday, markets closed), Playwright: opened from the sidebar; all three cards show value, change, sparkline (with hover crosshair and arrow-key stepping) and "Closed · updated Fri 17:00 / 15:00 ET"; polls every 3 s and stops when leaving the view; not-connected and backend-unreachable states (simulated by intercepting `/api/macro/state`, so the real TWS session was left alone) keep the values and mark them stale; layout checked at 760 px with the sidebar hidden.
  - 2026-10-19 00:20–00:25 ET (futures overnight session): the futures cards moved to the next 5-minute bar without a reload. Nothing streams on this account (no subscriptions, see design), so the streamed path itself can only be exercised once real-time data is subscribed.
- [x] 4.3 Note which data type each card showed (live / delayed / closed) and any IBKR errors in the change, so subscription gaps are visible before archiving
  - Paper account: IBKR answers 10167 ("not subscribed, displaying delayed data") for CL, NQ and TNX, so all three run on delayed data while open; no other errors. With markets closed, all three showed "closed" from daily bars, because delayed data streams nothing after hours. Historical bars work without the subscriptions.

## 5. Dow and VIX

- [x] 5.1 Add `YM` (CBOT `ContFuture`, pts, %) after NQ and `VIX` (CBOE `Index`, pts, %) after the 10Y yield to the indicator list, accept comma-separated sessions in the trading-hours parser, and add tests for VIX's two-session day and the five-indicator order; verify `uv run pytest` passes and `curl localhost:8000/api/macro/state` returns five indicators with values or IBKR errors
- [x] 5.2 Update the README feature list, market data section (CBOT, VIX) and the page description, and recheck the grid with five cards in the browser at wide and narrow widths; verify with Playwright screenshots
- [x] 5.3 Run `uv run pytest`, `npx tsc --noEmit -p .` and `npx vite build`; all pass

## 6. USD/COP (official TRM)

- [x] 6.1 Declare `httpx` as a runtime dependency; add `backend/macro/trm.py` (fetch the last 31 TRM rows from datos.gov.co, pick the row valid today in America/Bogota, previous rate, 30-point daily sparkline) and run it from the macro service in its own hourly loop (5 min after a failure, keeping the last rows), appending a USD/COP entry to `state()` with `freshness: "daily"`, `valid_from` / `valid_to` and per-card `stale: false`; add tests for picking the weekend row, the change against the previous rate, and a failed fetch keeping the last value with an error; verify `uv run pytest` passes and `curl localhost:8000/api/macro/state` shows the current TRM
- [x] 6.2 Renderer: add `'daily'` freshness and validity fields to the types, show "Official TRM · valid …" in the card footer, date-formatted sparkline tooltips for daily data, and per-card staleness (`unreachable || ind.stale`); verify tsc passes and the USD/COP card in Playwright screenshots
- [x] 6.3 Update the README (feature list, Macro data section noting the datos.gov.co request, API fields) and run `uv run pytest`, `npx tsc --noEmit -p .` and `npx vite build`; all pass

## 7. S&P 500 and spot indexes

- [x] 7.1 Add ES (CME `ContFuture`) after crude oil, and SPX (CBOE), NDX (NASDAQ) and INDU (CME) `Index` entries at the end of the indicator list; show a historical-data error (e.g. 162) on a card that has no value; add tests for the order and the no-value error; verify `uv run pytest` passes and `curl localhost:8000/api/macro/state` shows all ten cards with values or errors
- [x] 7.2 Update the README (features, Macro data section, CLAUDE.md symbol list) and the page description; check the ten-card grid in Playwright screenshots at wide and narrow widths, including the USD/COP card's "Official TRM · valid …" footer and date tooltip
- [x] 7.3 Run `uv run pytest`, `npx tsc --noEmit -p .` and `npx vite build`; all pass

## 8. Gold

- [x] 8.1 Add GC (COMEX `ContFuture`, $/oz) right after crude oil in the indicator list and update the order test; verify `uv run pytest` passes and `curl localhost:8000/api/macro/state` shows the GC front month with a value
- [x] 8.2 Update the README and the page check: the gold card in a Playwright screenshot; run `uv run pytest`, `npx tsc --noEmit -p .` and `npx vite build`; all pass

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, so `macro-indicators` becomes a main spec.
