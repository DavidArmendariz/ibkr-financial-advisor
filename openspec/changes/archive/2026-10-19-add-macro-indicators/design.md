# Design

## Context

All IBKR access goes through the single `ib_async` connection in `backend/services/ibkr_service.py`, with a supervisor that reconnects after drops. Existing features follow two patterns: Signals keeps a long-lived subscription (real-time bars) and pushes over a WebSocket; Gamma runs a background loop in a service object started from the `main.py` lifespan, exposes `GET /state`, and the renderer polls it (`useGamma`). `get_historical_bars` in `ibkr_service` only builds `Stock` contracts.

The Gamma service calls `reqMarketDataType(2)` (frozen) on the shared connection before each refresh. The market data type applies to `reqMktData` calls made after it, not to subscriptions already open.

## Goals / Non-Goals

**Goals:**
- Three always-on quotes with change vs previous close, a session sparkline and a clear live/delayed/closed label.
- No impact on Signals or Gamma (market data lines, pacing, market data type).

**Non-Goals:**
- A user-editable list of indicators or a settings form. The indicators are a module-level list, so adding DXY later is one entry plus whatever subscription it needs.
- Feeding macro values into the AI Advisor or the signal rules. A natural follow-up, but it changes those specs.
- Alerts or notifications on macro moves.
- Full-size interactive charts per indicator.

## Decisions

**10-year yield from the CBOE TNX index, not ZN futures or IBKR's bond quotes.** TNX is quoted as a yield, which is what the user asked for; the backend converts it to percent and computes the change in basis points. Alternative: the ZN 10-year note future. It is on the same CME subscription as NQ, but it is a price (≈110'00), moves inversely to yield, and converting it to a yield needs the cheapest-to-deliver bond, which is not something to approximate in the UI. Alternative: the on-the-run 10-year Treasury bond contract; IBKR's bond quotes need a separate bond data subscription and the contract changes at every auction. TNX's scale (CBOE has historically quoted it as yield × 10) is checked against a known value during implementation and the divisor kept in the indicator definition.

**Front month via `ContFuture`, then subscribe to the concrete `Future`.** `qualifyContractsAsync(ContFuture("CL", "NYMEX"))` returns the contract IBKR's continuous series is on, including its `conId` and `lastTradeDateOrContractMonth`; the service then streams that concrete contract (`reqMktData` does not accept `CONTFUT`). It re-qualifies once a day and on reconnect, and switches the subscription when the conId changes. Alternative: pick the nearest expiry from `reqContractDetails`. For CL that rolls too late (volume moves to the next month days before expiry) and would need per-product roll rules; IBKR's continuous series already encodes them.

**Dow from the YM future, not the DJIA cash index.** The CBOT E-mini Dow (YM) front month, resolved the same way as CL and NQ. It trades overnight, so before the open it shows the same pre-market move as NQ, and the two equity cards read alike. Alternative: the Dow Jones Industrial Average index (`INDU` on NYSE). It only updates 09:30–16:00 ET, so it would sit still exactly when the macro view is most useful, and it needs a separate index data permission.

**VIX from the CBOE index, not VX futures.** The VIX card shows the spot index, which is the number quoted everywhere, with its change in percent like the other prices. Alternative: the VX front-month future. It trades nearly around the clock, but it sits above or below spot depending on the term structure and rolls monthly, so it isn't the "VIX" people mean.

**Gold from the COMEX GC future, after crude oil.** IBKR's continuous GC contract points at the liquid month (GCZ6 in October 2026, 24,057 contracts that day against 30 and 123 in the expiring October and November months), so the same `ContFuture` resolution works without gold-specific roll rules. Alternative: spot gold (`XAUUSD` as an IBKR CMDTY). It's an OTC quote rather than an exchange price, and the futures are what trades overnight next to the other futures cards. It sits right after crude oil so the commodities are together.

**Spot indexes as separate cards at the end, next to their futures' source.** S&P 500 = `SPX` on CBOE, Nasdaq = `NDX` on Nasdaq (the index NQ tracks; the Nasdaq Composite `COMP` is also available if the broader index is wanted), Dow = `INDU` on CME (IBKR's symbol for the DJIA; it doesn't exist on NYSE). They only move during regular hours, so they sit after the round-the-clock instruments. The futures are still the "S&P/Nasdaq/Dow" cards that move pre-market. Without CME index permissions IBKR refuses even the Dow index's historical bars (162), so a card with no value shows that error rather than a blank.

**USD/COP from the official TRM on datos.gov.co, not an intraday quote.** IBKR has no Colombian peso contract at all (no `CASH` pair, index or future; checked on the paper account), so this one indicator comes from outside IBKR. The backend reads Banco de la República's TRM from the open-data portal's Socrata API (dataset `32sa-8pi3`: `valor`, `vigenciadesde`, `vigenciahasta`), the last 31 rows newest first, with no key. The card shows the row valid today in Bogotá time, its change against the row before, and the last 30 rates as the sparkline, labelled as the official daily rate with its validity dates instead of live/delayed/closed. Alternative: Yahoo Finance's `COP=X` gives intraday quotes, but the endpoint is undocumented, rate-limits and breaks without notice, and its terms don't cover app use. Alternative: leave USD/COP out; the user asked for it.

**TRM fetched in its own loop, independent of the IBKR connection.** A separate task fetches hourly (the TRM changes once a day, published in the afternoon for the next business day), and every 5 minutes after a failure, keeping the last good rows. It uses `httpx.AsyncClient` with a 10 s timeout. It doesn't wait for IBKR, so the card keeps working while IBKR refuses data or is disconnected, and isn't marked stale when IBKR drops; staleness becomes per card instead of a page-wide flag. Alternative: fetch on each `/state` poll; that would hit the portal every 3 s while the view is open.

**Streaming `reqMktData` subscriptions, not periodic snapshots.** Five lines out of ~100 is cheap, and streaming gives tick-level updates with `ticker.close` (previous close) and `ticker.marketDataType` for free. Alternative: snapshot requests every few seconds, like Gamma's `_spot`. Each snapshot costs a request and an 11 s wait when data is missing, and doesn't give the live/delayed state as cleanly.

**Market data type 4 (delayed-frozen) set immediately before subscribing.** IBKR returns live data when the account has it, delayed when not, and the last value when the market is closed, so every case shows something, and `ticker.marketDataType` tells the view which one it got. Because the type applies only at request time, Gamma's later `reqMarketDataType(2)` does not change these open subscriptions, and Gamma's own requests are unaffected since it sets its type before each refresh. Alternative: type 1 (live only). Without CME/CBOE subscriptions, the cards would just show errors 354/10089, which is the likely state of the user's account today.

**Sparkline from `reqHistoricalDataAsync`, every 5 minutes, outside the tick stream.** 1 day of 5-minute `TRADES` bars (TNX: `TRADES` on the index), `useRTH=False` for futures since they trade almost 24 h. `get_historical_bars` grows a `contract` parameter instead of a second copy of the request. Alternative: build the sparkline from the stream. It would be empty after every backend restart and outside trading hours. With the daily bars below that is 10 historical requests per 5 minutes for the five indicators, 20 per 10 minutes, inside IBKR's pacing limit of 60 per 10 minutes.

**Poll `GET /api/macro/state` every 3 s, not a WebSocket.** The service keeps the latest value per indicator; the view polls while mounted (same shape as `useGamma`). That gives the spec's 5 s bound with a few tiny requests while the view is open and nothing when it isn't. Alternative: a WebSocket like Signals. Signals needs one to push notifications to Electron even when the view is closed; Macro has no background consumer, so the extra protocol and reconnect handling buy little.

**Market open/closed from `tradingHours` per contract.** Futures and TNX have different hours from SOXL, so each indicator keeps the `tradingHours` from its own contract details, parsed as intervals in the contract's `timeZoneId` because futures sessions span midnight (`20261018:1800-20261019:1700`). Alternative: `liquidHours`, which Signals uses. For CL and NQ it only covers the day session (09:30–17:00 ET for CL), so the overnight session would show as closed. "Closed" in the view comes from these hours, not from the absence of ticks, so a quiet minute isn't shown as closed.

**Closed market falls back to daily bars.** Probing TWS showed that delayed data (types 3/4) streams nothing at all once the market is closed: no last value and no previous close. Each indicator therefore also fetches 5 days of daily bars with the sparkline; while the market is closed (or when nothing has streamed), the card shows the last daily close and the change against the close before it. A closed card ignores the stream even when it has values: overnight IBKR rolled VIX's stream to the next session, reporting Friday's close as both last and previous close (change 0) while SPX, also closed, still showed Friday's move. Alternative: rely on `reqMarketDataType(2)` frozen values. Frozen data needs a real-time subscription, which the account doesn't have for these exchanges.

**Errors per indicator.** The service listens to `ib.errorEvent` filtered by each ticker's `reqId` and stores the message on that indicator; a refused indicator is retried every 5 minutes (as Signals does), the others keep streaming.

**Sidebar position and icon.** Macro sits between Gamma and Settings so Settings stays last; icon `Globe` from lucide-react.

IBKR data permissions: real-time CL needs *NYMEX Real-Time*, GC needs *COMEX Real-Time*, NQ needs *CME Real-Time*, YM needs *CBOT Real-Time*, TNX and VIX need *CBOE Streaming Market Indexes* (or the US Securities Snapshot and Futures Value Bundle), all API-eligible and shared to paper. Without them IBKR's delayed data (10–15 min) is free for these exchanges. Market hours: CL, GC, ES, NQ and YM trade Sunday 18:00 to Friday 17:00 ET with a daily 17:00–18:00 break; TNX only during CBOE index hours; VIX has two CBOE sessions a day (03:15–09:15 and 09:30–17:00 ET).

## Risks / Trade-offs

- [The competing-live-session problem (10197) also blanks these cards] → Same as Signals: the error is shown on each card, and the README's existing advice applies.
- [TNX might not be available on the paper account even delayed] → The card shows IBKR's error; if that turns out to be the norm, fall back to computing a display from ZN in a follow-up change.
- [Without subscriptions nothing streams at all, even with the market open: probing NQ in the overnight session gave no ticks in 30 s with type 3/4, and `keepUpToDate` historical bars gave no updates either] → On this account every card moves only when the 5-minute bar refresh runs, with bars ~10 minutes behind; the card's "delayed · updated HH:MM" shows the bar time. Refreshing faster isn't worth it: ten IBKR cards × 2 requests would breach IBKR's 60 historical requests per 10 minutes, shared with Signals and the Dashboard, for data that is already 10–15 minutes old. Real-time needs the subscriptions in the README.
- [ContFuture qualification is ambiguous for some symbols (several exchanges)] → Exchange is fixed per indicator (NYMEX, CME), which makes it unique for CL and NQ.
- [Market data type 4 set by Macro could affect a later `reqMktData` from another feature that doesn't set its own type] → Today only Gamma calls `reqMktData`, and it sets type 2 first. Noted in CLAUDE.md's gotchas next to the existing Gamma line.
- [The app swaps the whole layout for the connection lock screen once `useConnection` (10 s polling) sees the drop] → The Macro view's own not-connected state covers that gap and the case where the backend is unreachable; the backend keeps the last streamed values, so the cards come back with them after reconnecting.
