# DeltaAdvisor

A local-first desktop application for portfolio monitoring, AI-powered financial advising, and real-time trade signal alerts, connected directly to Interactive Brokers via TWS or IB Gateway.

Built with Electron + React on the frontend and a Python FastAPI backend. The app runs entirely on your machine; the only data that leaves it is what the AI features send to the AI provider you choose (or nothing, with a local model). It never places orders.

---

## Features

**Dashboard**
- Real-time account summary: Net Liquidation Value, Unrealized P&L, Realized P&L, Buying Power
- Sortable positions table with ticker, asset class, quantity, average cost, market price, and P&L
- Interactive candlestick chart (TradingView `lightweight-charts`) with 1D / 5D / 1M / 3M / 1Y timeframes; click any position row to load its chart

**AI Financial Advisor**
- Acts as an expert portfolio manager following Aswath Damodaran's investment process: understand the client, set the asset allocation before selecting securities, weigh trading costs and taxes, and judge performance against risk
- **Risk profile** dropdown (Conservative / Moderate / Aggressive) above the message box, sent with every message and remembered between sessions. Each profile sets allocation ranges, loss tolerance, single-position caps, and whether margin or options are acceptable
- Each message automatically injects a live snapshot of your portfolio (positions, P&L, cash) into the system prompt
- Replies render full markdown (tables, lists, links) and can include charts: allocation breakdowns, current-vs-target bars, and projections drawn from numbers the advisor supplies, plus live price charts loaded from IBKR (never invented by the model). Every chart has a table view
- Choose the provider in **Settings**: Anthropic (Claude), or any OpenAI-compatible API: OpenRouter (hundreds of models behind one key), OpenAI, or a local model via Ollama / LM Studio
- Real-time streaming responses via WebSocket
- Persistent chat sessions stored in a local SQLite database; create, switch between, and delete conversations (deletion is confirmed in a dialog)

**Signals (SOXL real-time alerts)**
- Streams 5-second real-time bars for SOXL and combines them into 1-minute bars (timeframe configurable), after warming up from historical data
- Computes indicators incrementally on each closed bar: session VWAP (from 09:30 ET, or 04:00 ET with pre-market), EMA 9 / 21, Bollinger Bands (20, 2σ), and relative volume
- **LONG entry** signal when the close crosses above VWAP, EMA fast is above EMA slow, and relative volume is above a threshold. No signals in the first and last 10 minutes of the session (using IBKR's actual trading hours, so half-days are handled), with a 5-minute cooldown; all configurable
- Optional **LLM filter**: each signal's snapshot (price, indicators, last 20 bars) goes to the AI provider configured in **Settings**, which answers take/skip with a confidence and a short reason. Only signals it takes above a confidence threshold are notified. On a timeout (5 s), invalid reply, or no configured provider, the signal passes through marked `unfiltered`
- Native desktop notification for each alert, e.g. `SOXL LONG ENTRY @ 167.39`, with the key indicator values and the LLM's reason. Clicking it opens the Signals view. Alerts arrive even while the window is closed, as long as the app is running
- The **Signals** view shows the IBKR connection, market data and LLM filter status, live indicator values, the last 50 signals with their LLM decisions, and all settings (applied live, no restart)
- Alerts only: no orders are placed

**TWS Connection Guard**
- On launch, auto-connects to a **paper** TWS / IB Gateway session on `127.0.0.1:7497`, connecting read-only. Live (`7496`) is never connected automatically; use the **Live** button on the lock screen
- If an established connection drops (for example during TWS or IB Gateway's daily restart), the backend reconnects on its own, retrying with increasing waits up to 60 seconds, and the Signals stream resubscribes
- While disconnected, shows a lock screen with setup instructions and keeps retrying paper every 10 seconds, so the app connects on its own once TWS is started
- Live connection indicator and Net Liquidation Value always visible in the sidebar footer

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | Electron 34 |
| Frontend | React 18, Vite 6, Tailwind CSS v4, Shadcn UI |
| IBKR connectivity | Python 3.12, `ib_async` |
| API server | FastAPI, Uvicorn |
| AI | Anthropic Claude (`anthropic` SDK) or any OpenAI-compatible API (`openai` SDK): OpenRouter, OpenAI, Ollama, LM Studio |
| Charts | `lightweight-charts` (price), Recharts (advisor charts) |
| Database | SQLite via SQLModel + aiosqlite |
| Tests | pytest, pytest-asyncio, pandas (reference values) |
| Python env | `uv` |
| Node env | `nvm` (pinned to v20) |
| macOS packaging | electron-builder + PyInstaller |

---

## Prerequisites

| Tool | Install |
|---|---|
| Node.js v20 | `nvm install 20` |
| Python 3.12+ | [python.org](https://www.python.org/downloads/) or `brew install python@3.12` |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| nvm | [github.com/nvm-sh/nvm](https://github.com/nvm-sh/nvm#installing-and-updating) |
| TWS or IB Gateway | [interactivebrokers.com](https://www.interactivebrokers.com/en/trading/tws.php) |

---

## Setup

### 1. Node version

```bash
nvm install 20   # first time only
nvm use          # reads .nvmrc
```

### 2. Install Node dependencies

```bash
npm install
```

### 3. Set up the Python environment

```bash
uv sync
# creates .venv and installs all dependencies from pyproject.toml
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values. The AI settings can be left empty here and set from the app's **Settings** tab instead: keys and endpoints are verified, then written back to this file.

```env
ANTHROPIC_API_KEY=sk-ant-...
IBKR_PAPER_PORT=7497    # paper trading (used by auto-connect)
IBKR_LIVE_PORT=7496     # live trading
IBKR_CLIENT_ID=1
BACKEND_PORT=8000
```

Signal settings are stored in the same file as `SIGNALS_*` keys (for example `SIGNALS_RVOL_THRESHOLD=1.5`) when you save them from the **Signals** view. They're optional; without them the defaults below apply.

| Setting | Default |
|---|---|
| `SIGNALS_TIMEFRAME_MINUTES` | `1` (1, 2, 3, 5, 10, 15 or 30) |
| `SIGNALS_EMA_FAST` / `SIGNALS_EMA_SLOW` | `9` / `21` |
| `SIGNALS_BB_PERIOD` / `SIGNALS_BB_STD` | `20` / `2.0` |
| `SIGNALS_RVOL_PERIOD` / `SIGNALS_RVOL_THRESHOLD` | `20` bars / `1.5` |
| `SIGNALS_INCLUDE_PREMARKET` | `false` |
| `SIGNALS_OPEN_BLACKOUT_MINUTES` / `SIGNALS_CLOSE_BLACKOUT_MINUTES` | `10` / `10` |
| `SIGNALS_COOLDOWN_MINUTES` | `5` |
| `SIGNALS_LLM_ENABLED` / `SIGNALS_LLM_CONFIDENCE_THRESHOLD` | `false` / `0.6` |
| `SIGNALS_LLM_MODEL_ANTHROPIC` | `claude-haiku-4-5-20251001` |
| `SIGNALS_LLM_MODEL_OPENAI` | `gpt-4.1-mini` |
| `SIGNALS_LLM_MODEL_OPENROUTER` | `anthropic/claude-haiku-4.5` |

A local model (Ollama, LM Studio) uses the model set in **Settings**.

### 5. Configure TWS / IB Gateway

The TWS API socket is **off by default**. While it's off, TWS can be running and logged in and the app still shows its "not connected" lock screen: nothing is listening on the API port.

1. Log in to TWS. For testing, choose **Paper Trading**; a red "paper trading account" banner confirms it.
2. Open **File → Global Configuration**. The dialog title reads *Trader Workstation Configuration (Simulated Trading)* when you're in paper mode.
3. In the left tree, go to **Configuration → API → Settings**.
4. The first time, TWS shows an **API announcements** pop-up. Click **OK** (optionally tick *Don't display this message again*). One of its notices explains that TWS uses **different ports for paper and live accounts**, which is why the app tries `7497` and then `7496`.
5. Under **General**, set:

   | Setting | Value | Why |
   |---|---|---|
   | **Enable ActiveX and Socket Clients** | ✅ on | Opens the API socket; required |
   | **Socket port** | `7497` (paper) / `7496` (live) | Must match `IBKR_PAPER_PORT` / `IBKR_LIVE_PORT` in `.env`. Scroll down in the panel to find it |
   | **Read-Only API** | ✅ on is fine | The app only reads positions, balances, and market data today. Turn it off only if order placement is added later |
   | **Allow connections from localhost only** | ✅ on | Keeps the API off the network. Or add `127.0.0.1` to **Trusted IPs** |

   Further down the panel, **Use "$LEDGER" prefix for per-currency keys** can be on or off; the app handles both.

   Some advanced options are collapsed behind **Some options are hidden…** at the bottom of the panel; the defaults there are fine.
6. Click **Apply**, then **OK**. The socket opens immediately; no TWS restart is needed.
7. The first time the app connects, TWS may ask whether to **accept an incoming API connection**. Click **Accept**. Adding `127.0.0.1` to Trusted IPs avoids the prompt.

**Check that the socket is open:**

```bash
lsof -nP -iTCP:7497 -sTCP:LISTEN   # should list the TWS (Java) process
```

**Troubleshooting**

- **Nothing listening on 7497/7496**: the API isn't enabled (step 5), TWS is still logging in, or you set a different socket port.
- **Pop-up: "An API client is attempting to send a request that needs API write access"**: click **Close** and leave Read-Only API on. The app connects in read-only mode and makes no write requests, so this only appears if another tool (or an older build of this app) asks TWS for orders.
- **Connects, then drops immediately**: another API client is using the same client ID. Change `IBKR_CLIENT_ID` in `.env`.
- **Connection lost overnight**: TWS logs off or restarts once a day (configurable under **Configuration → Lock and Exit**). The backend keeps retrying; once TWS is back and logged in, the app reconnects on its own.
- **IB Gateway** works the same way, but its default ports are `4002` (paper) and `4001` (live). Either change them to 7497/7496 in the Gateway's API settings, or set `IBKR_PAPER_PORT` / `IBKR_LIVE_PORT` in `.env`.

### 6. Market data for Signals

The Signals view needs **real-time** market data for SOXL, which trades on NYSE Arca (IBKR lists it under `AMEX`). Historical bars and the Dashboard work without it, but the 5-second real-time bar stream is refused, and the Signals view shows the IBKR error (for example `420: No market data permissions for AMEX STK` or `10089: Requested market data requires additional subscription for API`). The app retries every 5 minutes.

- Subscribe to a market data package that covers NYSE Arca for API use, from the market data subscriptions page in the IBKR Client Portal. TWS's **Market Data Connections** dialog (linked from the error) shows what's missing.
- For a **paper** account, also turn on sharing of the live account's market data with the paper account (in the Client Portal's paper trading account settings). Paper accounts have no subscriptions of their own.

---

## Running in Development

```bash
npm run dev
```

This starts three processes concurrently:

| Process | Command | Port |
|---|---|---|
| Python backend | `uv run uvicorn backend.main:app --reload --reload-dir backend` | 8000 |
| Vite dev server | `vite` | 5273 |
| Electron | waits for both ports, then launches | — |

React changes apply instantly via HMR. Python changes under `backend/` trigger a backend reload automatically. Open DevTools from the Electron window for frontend debugging.

Before starting, `npm run dev` runs `scripts/kill-stale-backend.sh`, which stops a dev backend from a previous run that didn't shut down and is still holding port 8000. It only touches processes from this repo's `.venv`.

Closing the window with the red button keeps the app running in the Dock (signal notifications keep arriving). Quit with **Cmd+Q** to stop all three processes.

You can also start services individually:

```bash
npm run dev:backend    # Python only
npm run dev:frontend   # Vite only
npm run dev:electron   # Electron only (assumes backend + Vite are already up)
```

---

## Tests

```bash
uv run pytest
```

Covers the indicators (checked against pandas on fixed data), bar aggregation, each signal rule (crossing, blackout, cooldown, session boundaries), settings validation, and the LLM filter (mocked replies, timeout, invalid JSON, missing provider). No IBKR connection or API key is needed.

## Signal replay

Replay past bars through the same pipeline the live stream uses, printing signals instead of notifying, to sanity-check the rules:

```bash
uv run python -m backend.signals.replay --date 2026-10-05          # fetch a session from IBKR
uv run python -m backend.signals.replay --date 2026-10-05 --llm    # also run each signal through the LLM filter
uv run python -m backend.signals.replay --csv bars.csv              # your own bars
uv run python -m backend.signals.replay --date 2026-10-05 --timeframe 5
```

- `--date` connects to TWS / IB Gateway on the paper port with its own client ID (`IBKR_CLIENT_ID` + 50), so it can run alongside the app. Earlier sessions are loaded for indicator warm-up, and signals are only reported for the chosen day.
- `--csv` expects a header row `time,open,high,low,close,volume`. `time` is the bar start, as ISO 8601 (no offset means US Eastern) or a Unix timestamp.
- Replay uses the settings saved from the Signals view. It assumes regular 09:30-16:00 hours, so early closes aren't detected.
- `--llm` makes one real call per signal to your configured AI provider.

---

## macOS Build & Packaging

```bash
npm run package:mac
```

This runs three steps in order:

1. `npm run package:backend` — PyInstaller freezes the FastAPI server into a standalone binary at `backend-dist/server` (no Python needed on the target machine)
2. `npm run build` — builds the React app into `dist/`
3. `electron-builder --mac` — bundles everything into a `.dmg` in `dist-electron/`

The build targets the **host architecture only** (e.g. arm64 on Apple Silicon). The PyInstaller binary is native to the machine that froze it, so build on an Intel Mac to get an x64 build.

For a quicker local check, skip the `.dmg` and build just the `.app`:

```bash
npm run package:backend && npm run build && npx electron-builder --mac --dir
open "dist-electron/mac-arm64/DeltaAdvisor.app"
```

### How the packaged app runs

- Electron spawns the bundled backend on `127.0.0.1:8000`, waits for `/api/health`, then opens the window. If the backend fails to start or exits, an error dialog is shown.
- On quit, Electron asks the backend to stop and force-kills it if it hasn't exited after 5 seconds. If the app crashed or was force-quit, the next launch stops the leftover backend first (tracked in `backend.pid` in the user data folder).
- The first signal notification triggers macOS's notification permission prompt; allow it to see alerts.
- The renderer is served from the custom `app://bundle` scheme (not `file://`), which is the origin the backend's CORS policy allows.
- The backend runs with its working directory set to the user data folder, `~/Library/Application Support/ibkr-financial-advisor/`. A template `.env` is created there on first launch; AI keys entered in **Settings** and signal settings are saved to it (owner-only permissions). The SQLite database (chats and signal history) lives there too.

The app is not code-signed; macOS may require right-click → **Open** the first time. The app icon is `assets/icon.icns`, generated from `assets/icon.svg` (the DeltaWits mark); `assets/icon.png` is used as the Dock icon in development.

---

## Project Structure

```
ibkr-financial-advisor/
│
├── electron/
│   ├── main.cjs                  # Electron main process; spawns backend + serves app:// in prod
│   ├── preload.cjs               # contextBridge API surface
│   └── signal-notifications.cjs  # Subscribes to signal events, shows native notifications
│
├── backend/
│   ├── main.py           # FastAPI app + lifespan (DB init, reconnect supervisor, signal service)
│   ├── config.py         # Settings via pydantic-settings + .env
│   ├── database.py       # SQLite engine; ChatThread, ChatMessage, SignalEvent models
│   ├── routers/
│   │   ├── connection.py # GET /status, POST /connect, POST /auto-connect
│   │   ├── portfolio.py  # GET /summary, /positions, /snapshot, /chart/:symbol
│   │   ├── chat.py       # REST thread CRUD + WS /ws/:thread_id streaming
│   │   ├── settings.py   # AI provider selection, Anthropic key, OpenAI-compatible config
│   │   └── signals.py    # GET /state, PUT /settings, WS /ws
│   ├── services/
│   │   ├── ibkr_service.py   # ib_async singleton; connect, auto-reconnect, positions, bars
│   │   └── ai_service.py     # Advisor prompt (risk profiles, charts) + Anthropic / OpenAI-compatible streaming
│   └── signals/
│       ├── service.py        # Warm-up, real-time bar subscription, LLM filtering, broadcasting
│       ├── pipeline.py       # Bars → indicators → rules → signal snapshots (shared with replay)
│       ├── indicators.py     # Incremental EMA, Bollinger, session VWAP, relative volume
│       ├── bars.py           # 5-second → N-minute bar aggregation
│       ├── rules.py          # Pure signal rules: crossing, blackout, cooldown
│       ├── sessions.py       # Trading hours from IBKR liquidHours
│       ├── llm_filter.py     # Provider abstraction + take/skip decision
│       ├── config.py         # SIGNALS_* settings, validation, persistence
│       └── replay.py         # CLI: replay CSV or a past session
│
├── tests/                # pytest suite for indicators, bars, rules, LLM filter
├── scripts/
│   └── kill-stale-backend.sh # Run before `npm run dev`
│
└── src/
    ├── App.tsx               # ConnectionGuard gate → Layout
    ├── types/index.ts        # Shared TypeScript interfaces
    ├── lib/
    │   ├── api.ts            # Axios + WebSocket client
    │   └── utils.ts          # cn(), formatCurrency(), pnlClass()
    ├── hooks/
    │   ├── useConnection.ts  # Polls /api/connection/status every 10 s
    │   ├── usePortfolio.ts   # Polls summary + positions every 15 s
    │   ├── useChat.ts        # Thread CRUD + WebSocket streaming state
    │   └── useSignals.ts     # Signals WebSocket: status, live values, history, settings
    ├── components/
    │   ├── ConnectionGuard.tsx
    │   ├── Sidebar.tsx
    │   ├── Layout.tsx
    │   ├── DeltaWitsMark.tsx # Sidebar logo
    │   ├── ui/               # Shadcn primitives (button, card, dialog, …)
    │   ├── dashboard/        # AccountSummary, PositionsTable, TradingChart
    │   ├── chat/             # Session list, chat window, markdown + chart rendering, risk profile select
    │   └── signals/          # Status cards, live values, signal table, settings form
    └── pages/
        ├── Dashboard.tsx
        ├── Chat.tsx
        ├── Signals.tsx
        └── Settings.tsx
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/connection/status` | Current TWS connection state |
| `POST` | `/api/connection/auto-connect` | Try paper port, fall back to live (no-op if already connected) |
| `POST` | `/api/connection/connect` | Connect to a specific mode (`paper`/`live`) |
| `GET` | `/api/portfolio/summary` | Account tags (NLV, P&L, buying power) |
| `GET` | `/api/portfolio/positions` | All open positions with market data |
| `GET` | `/api/portfolio/snapshot` | Summary + positions in one call |
| `GET` | `/api/portfolio/chart/:symbol` | OHLCV bars (`?duration=1 D&bar_size=5 mins`) |
| `GET` | `/api/chat/threads` | List all chat sessions |
| `POST` | `/api/chat/threads` | Create a new session |
| `DELETE` | `/api/chat/threads/:id` | Delete session + messages |
| `GET` | `/api/chat/threads/:id/messages` | Full message history |
| `WS` | `/api/chat/ws/:thread_id` | Streaming chat (send `{"message":"…"}`) |
| `GET` | `/api/settings` | Active AI provider and its configuration; keys only as set/`…abcd` hint, never the key |
| `PUT` | `/api/settings/ai-provider` | Select the provider (`{"provider":"anthropic" \| "openai_compatible"}`) |
| `PUT` | `/api/settings/anthropic-api-key` | Verify a key with Anthropic and save it (`{"api_key":"…"}`) |
| `PUT` | `/api/settings/openai-compatible` | Verify and save `{"base_url","model","api_key"}` (omit `api_key` to keep the saved one, `""` to clear it) |
| `GET` | `/api/signals/state` | Signal status, live indicator values, last 50 signals, and settings |
| `PUT` | `/api/signals/settings` | Update any subset of signal settings; applied live |
| `WS` | `/api/signals/ws` | Signal event stream (see below) |

---

## WebSocket Chat Protocol

**Client → Server**
```json
{ "message": "Should I rebalance my tech exposure?", "risk_profile": "moderate" }
```

`risk_profile` is `conservative`, `moderate`, or `aggressive`; it defaults to `moderate`.

**Server → Client**
```json
{ "type": "start" }
{ "type": "chunk", "content": "Based on your current " }
{ "type": "chunk", "content": "positions…" }
{ "type": "done" }
```

Error frame: `{ "type": "error", "content": "…" }`

## WebSocket Signals Protocol

Server → client only. On connect the server sends the full state, then events as they happen:

```json
{ "type": "init", "status": {…}, "live": {…}, "history": [ … ], "settings": {…} }
{ "type": "status", "status": { "ib": "connected", "stream": "streaming", "error": null, "llm": { "enabled": true, "provider": "anthropic", … } } }
{ "type": "live", "live": { "last_price": 167.4, "indicators": { "vwap": 166.9, "ema_fast": 166.7, … } } }
{ "type": "signal", "notify": true, "signal": { "signal_type": "LONG_ENTRY", "price": 167.39, "indicators": {…}, "bars": [ … ], "llm": { "action": "take", "confidence": 0.72, "reason": "…" } } }
{ "type": "settings", "settings": {…} }
```

`notify` is true when the signal should alert: the LLM filter is off, the signal is `unfiltered`, or the LLM took it at or above the confidence threshold.

---

## Notes

- **Paper vs Live** — the app only auto-connects to paper (`7497`). Connecting to live (`7496`) always takes an explicit click. Never use live credentials for testing.
- **API key security** — API keys live in `.env` (owner-only permissions) and are only read by the local Python process. The Settings screen can write a new key, but the backend never sends a stored key back to the renderer.
- **What leaves your machine** — portfolio data, chat history, and signal history are stored locally. Each AI Advisor message sends the conversation plus a snapshot of your positions, P&L, and balances to the selected AI provider. With the LLM filter on, each signal sends its SOXL price, indicator values, and last 20 bars (market data only, nothing about your account). With OpenRouter, requests also pass through OpenRouter to the model's provider; its privacy settings can restrict routing to providers that don't train on or retain data. A local model (Ollama, LM Studio) keeps everything on your machine.
- **Signals are alerts, not advice** — the rules are mechanical and the LLM filter only judges each precomputed snapshot. The app places no orders.
- **Model IDs** — the OpenAI-compatible model must be an ID the endpoint lists (e.g. `vendor/model-name` on OpenRouter). OpenRouter lists models without checking the key, so a wrong OpenRouter key only shows up as an error on the first chat message.
- **Multiple IB clients** — if another app (e.g. the TWS API demo) is connected with `clientId=1`, change `IBKR_CLIENT_ID` in `.env` to avoid conflicts.
