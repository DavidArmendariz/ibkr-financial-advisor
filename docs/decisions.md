# Decision log (before OpenSpec)

Decisions made before the project adopted OpenSpec on 2026-10-10. New decisions are recorded in each change's `design.md` under `openspec/changes/` (archived changes keep them). Behavior itself is specified in `openspec/specs/`.

Newest first. Each entry: what was decided, why, and what it costs. If one of these is reversed, note it here as superseded and link the OpenSpec change that replaced it.

---

## 2026-10-09 — Signals chart: history kept in the pipeline, times shown in New York time

**Decision.** The signal pipeline keeps the last 1,500 bars with their indicator values; the Signals view draws them with `lightweight-charts`, plus the forming candle every 5 s. Timestamps are shifted from UTC to US/Eastern before plotting.

**Why.** The chart must show exactly what the rules saw, so it reuses the pipeline's own values instead of recomputing indicators in the browser. `lightweight-charts` has no time-zone support, and a UTC axis (13:30–20:00) is confusing for a US session.

**Cost.** Shifted timestamps are only correct for display; never send them back to the backend.

## 2026-10-09 — Gamma exposure: conventions and data handling

**Decision.**
- Exposure per option = gamma × open interest × 100 × spot² × 1% (dollar gamma per 1% move). Calls positive, puts negative.
- Gamma and implied volatility come from IBKR model greeks; the zero-gamma level re-prices every option with Black–Scholes from its own IV across ±30% of spot.
- Default window: expirations within 45 days, strikes within ±25% (~950 contracts), fetched in batches of 80, refreshed every 15 min during market hours.
- Open interest is cached per contract in SQLite and reused when IBKR doesn't report it; the view warns when coverage is below 80%.

**Why.** The sign convention assumes dealers are long calls and short puts — the common simplification, stated in the UI. Re-pricing with Black–Scholes was checked against IBKR's own gamma (within 3%). IBKR reports open interest only while the market is open, and it only changes daily, so a cache keeps after-hours and weekend views usable. Batches stay under the ~100 market data line limit.

**Cost.** Exposure is an estimate built on a positioning assumption. A refresh takes minutes, not seconds.

## 2026-10-07 — Cap backend graceful shutdown at 5 seconds

**Decision.** uvicorn runs with a 5 s graceful-shutdown timeout in dev and in the packaged backend.

**Why.** Dev reloads repeatedly hung on "Waiting for background tasks to complete". Five isolated reproductions (open WebSockets, live streaming, abandoned sockets, reload) all shut down cleanly, so the stuck task was never identified. The likeliest suspect is a request waiting forever on IBKR (see error 322 in CLAUDE.md). The timeout bounds the damage regardless of cause.

**Cost.** A genuinely slow request is cancelled at shutdown. Root cause still open.

## 2026-10-07 — Reconnect re-checks its target under the connection lock

**Decision.** The reconnect supervisor goes through `reconnect()`, which re-checks under the lock that the app is still disconnected and still aimed at the same port.

**Why.** A retry queued for paper could run right after the user connected to live, drop the live connection, and leave the app disconnected. Reproduced in a test before fixing.

## 2026-10-06 — Real-time data: Network B and OPRA, shared from the live account

**Decision.** Live signals and gamma need the paid *Network B* (stocks on NYSE American/Arca, ~$1.50/mo) and *OPRA* (options) subscriptions on the live user, shared to the paper account. Market data permission errors back off for 5 minutes.

**Why.** The free non-consolidated feed is not API-eligible; paper accounts have no subscriptions of their own. Permission errors don't resolve quickly, so retrying every 30 s only adds noise.

## 2026-10-06 — Signals: deterministic rules, LLM only as an optional filter

**Decision.**
- Signals come from pure rule functions over incrementally computed indicators. Only **LONG entry** is implemented; exit rules were deferred at the user's request.
- The optional LLM filter judges a precomputed snapshot and returns `{action, confidence, reason}`. It never computes indicators.
- It fails open: timeout (5 s), invalid JSON, provider error or no configured provider → the signal is notified as `unfiltered`.
- Indicators are hand-written incremental classes (not `talipp`), tested against pandas. Bollinger uses population standard deviation.
- Bars are 5-second real-time bars aggregated into clock-aligned buckets; incomplete buckets are dropped. Verified equal to IBKR's own 1-minute history (OHLCV identical).

**Why.** Deterministic rules are testable and replayable; the LLM only adds judgment. Failing open means a broken or unconfigured provider never silently suppresses alerts.

**Cost.** Roughly one signal per day at default settings (replays of five sessions: 1, 1, 1, 1, 0).

## 2026-10-06 — LLM filter reuses the app's AI settings and runs in the backend

**Decision.** The filter uses whatever provider is configured in Settings: Anthropic via the `anthropic` SDK with structured outputs (default `claude-haiku-4-5-20251001`); OpenAI or OpenRouter via the `openai` SDK (defaults `gpt-4.1-mini`, `anthropic/claude-haiku-4.5`); a local server uses the model set in Settings. Output is capped at 256 tokens.

**Why.** Keys already live only in the backend, so nothing secret crosses to Electron. `gpt-4.1-mini` was chosen over `gpt-5-mini` because it doesn't reason first and fits the 5 s timeout. Without an explicit token cap, OpenRouter reserves the model's full output budget against the account balance and returns 402 on low-credit accounts.

## 2026-10-06 — Native notifications come from Electron's main process

**Decision.** The main process subscribes to `/api/signals/ws` itself (using the `ws` package) and shows `Notification`s; clicking one opens the Signals view.

**Why.** Alerts keep arriving when the window is closed but the app is still in the Dock. Electron 34's Node 20 has no global `WebSocket`.

## 2026-10-06 — Migrate from ib_insync to ib_async, one shared connection

**Decision.** All IBKR access goes through one `ib_async` `IB()` instance, with a supervisor that reconnects (1 s → 60 s backoff) after unexpected drops.

**Why.** `ib_async` is the maintained fork with the same API. One connection avoids juggling client IDs and duplicate event loops.

## 2026-10-06 — AI Advisor charts are fenced blocks; price data is never model-generated

**Decision.** The advisor can emit ```` ```chart ```` blocks (allocation / bar / line, numbers it supplies) and ```` ```price-chart ```` blocks (symbol + period) that the UI fills with IBKR history.

**Why.** Charts of the advisor's own proposals help; charts of market prices must be real data, so the model only names what to plot.

## 2026-10-06 — Advisor persona: Damodaran-style portfolio manager with explicit risk profiles

**Decision.** The system prompt follows Damodaran's process (understand the client → allocation before security selection → execution costs → evaluate against risk). Three risk profiles (Conservative / Moderate / Aggressive) define allocation ranges, loss tolerance, position caps and margin/options rules, sent with every message.

**Why.** Concrete, bounded guidance per profile produces consistent advice; sending the profile per message lets the user switch mid-conversation.

## 2026-09-26 — Packaged backend lifecycle

**Decision.** On quit Electron sends SIGTERM to the backend's process group and SIGKILLs it after 5 s; the backend PID is recorded in `backend.pid` so a crashed run's leftover backend is killed on the next launch (only if that PID is still our binary).

**Why.** The PyInstaller one-file binary is a bootloader plus a child process, and an orphaned backend holds port 8000.

## 2026-09-26 — Rename to DeltaAdvisor without moving user data

**Decision.** User-facing names became DeltaAdvisor; the npm package name, app ID and data folder (`~/Library/Application Support/ibkr-financial-advisor/`) stayed.

**Why.** Renaming the data folder would orphan the saved API key and chat history.

## 2026-09-26 — Safety boundaries

**Decision.** IBKR connections are read-only; there is no order-placement code. Auto-connect only targets the paper port. API keys are stored in `.env` with owner-only permissions and never returned to the renderer.

**Why.** The app handles a real brokerage account; mistakes here are costly and hard to undo.
