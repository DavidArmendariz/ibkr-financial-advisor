# Proposal

## Why

SOXL is a 3× leveraged semiconductor ETF, so it reacts strongly to the wider market: equity futures, oil, gold, rates and volatility move it before and during the session. Today the user has to check those in another app. A Macro view puts crude oil, Nasdaq 100 and Dow futures, the 10-year Treasury yield and the VIX next to the rest of the app, live, from the same IBKR connection, plus the official USD/COP rate.

## What Changes

- New **Macro** item in the sidebar, between Gamma and Settings, opening a Macro view.
- The view shows one card per indicator:
  - **Crude oil (CL)**: NYMEX WTI front-month future, in $/bbl.
  - **Gold (GC)**: COMEX gold front-month future, in $/oz.
  - **S&P 500 futures (ES)**: CME E-mini S&P 500 front-month future, in index points.
  - **Nasdaq 100 futures (NQ)**: CME E-mini Nasdaq-100 front-month future, in index points.
  - **Dow Jones futures (YM)**: CBOT E-mini Dow front-month future, in index points.
  - **US 10-year yield**: CBOE 10-year Treasury yield index (TNX), shown as a percent with the change in basis points.
  - **VIX**: CBOE Volatility Index, in index points.
  - **USD/COP**: Banco de la República's official daily rate (TRM), from Colombia's open-data portal (datos.gov.co), because IBKR doesn't offer the Colombian peso.
  - At the end, the spot indexes: **S&P 500** (SPX, CBOE), **Nasdaq 100** (NDX, Nasdaq) and **Dow Jones Industrial Average** (INDU, CME).
- Each card shows the last value, the change and percent change since the previous close, an intraday sparkline, whether the data is live, delayed or the last close (market closed), and the IBKR error when data is refused.
- Front-month futures roll over automatically; the card names the contract month in use.
- New backend service streaming the ten IBKR quotes from the shared IBKR connection and fetching the TRM, with a `GET /api/macro/state` endpoint the view polls.

## Capabilities

### New Capabilities
- `macro-indicators`: live macro market indicators (crude oil, gold, S&P 500, Nasdaq 100 and Dow futures and spot indexes, 10-year Treasury yield, VIX from IBKR; USD/COP from the official TRM) shown in their own view.

### Modified Capabilities
None. `app-navigation` describes hiding and showing the sidebar, not its list of items, so adding an item does not change its requirements.

## Impact

- **Backend:** new `backend/macro/` (service + contract resolution + TRM fetcher), `httpx` declared as a runtime dependency (already installed through the AI SDKs), `backend/routers/macro.py`, service start/stop in `backend/main.py` lifespan; tests for the formatting/change math and the rollover choice.
- **Renderer:** `AppTab` gets `'macro'`; new `pages/Macro.tsx`, `hooks/useMacro.ts`, `components/macro/`; Sidebar and Layout entries; API client + types.
- **IBKR:** read-only market data only (`reqMktData`, `reqHistoricalData`, contract details). Uses 10 of the ~100 market data lines. No orders, no account data. Real-time CL/GC/ES/NQ/YM need NYMEX/COMEX/CME/CBOT futures subscriptions, TNX/VIX/SPX need CBOE index data, NDX needs Nasdaq index data and the Dow index needs CME index data (IBKR refuses even its historical bars without it); without them IBKR's free delayed data is used and labelled as delayed.
- **Data leaving the machine:** a public, unauthenticated GET to `www.datos.gov.co` for the latest TRM rates, at most once an hour (every 5 minutes after a failure). It carries only the dataset query, no account, position or user data.
- **Hard constraints:** IBKR access stays `readonly=True` and nothing places orders; no API keys or LLM calls are involved; auto-connect is untouched.
- **Docs:** README feature list, market data section and API reference.
