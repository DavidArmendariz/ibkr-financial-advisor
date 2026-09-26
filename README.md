# DeltaAdvisor

A local-first desktop application for trading and AI-powered financial advising, connected directly to Interactive Brokers via TWS or IB Gateway.

Built with Electron + React on the frontend and a Python FastAPI backend. The app runs entirely on your machine; the only data that leaves it is what the AI Advisor sends to the AI provider you choose (or nothing, with a local model).

---

## Features

**Dashboard**
- Real-time account summary: Net Liquidation Value, Unrealized P&L, Realized P&L, Buying Power
- Sortable positions table with ticker, asset class, quantity, average cost, market price, and P&L
- Interactive candlestick chart (TradingView `lightweight-charts`) with 1D / 5D / 1M / 3M timeframes; click any position row to load its chart

**AI Financial Advisor**
- Persistent chat sessions stored in a local SQLite database
- Each message automatically injects a live snapshot of your portfolio (positions, P&L, cash) into the system prompt
- Choose the provider in **Settings**: Anthropic (Claude), or any OpenAI-compatible API: OpenRouter (hundreds of models behind one key), OpenAI, or a local model via Ollama / LM Studio
- Real-time streaming responses via WebSocket
- Session sidebar: create, switch between, and delete conversations

**TWS Connection Guard**
- On launch, auto-connects to a **paper** TWS / IB Gateway session on `127.0.0.1:7497`, connecting read-only. Live (`7496`) is never connected automatically; use the **Live** button on the lock screen
- While disconnected, shows a lock screen with setup instructions and keeps retrying paper every 10 seconds, so the app connects on its own once TWS is started (or logs back in after its daily restart)
- Live connection indicator and Net Liquidation Value always visible in the sidebar footer

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | Electron 34 |
| Frontend | React 18, Vite 6, Tailwind CSS v4, Shadcn UI |
| IBKR connectivity | Python 3.12, `ib_insync` |
| API server | FastAPI, Uvicorn |
| AI | Anthropic Claude (`anthropic` SDK) or any OpenAI-compatible API (`openai` SDK): OpenRouter, OpenAI, Ollama, LM Studio |
| Database | SQLite via SQLModel + aiosqlite |
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
- **Connection lost overnight**: TWS logs off or restarts once a day (configurable under **Configuration → Lock and Exit**). Log back in and the app reconnects.
- **IB Gateway** works the same way, but its default ports are `4002` (paper) and `4001` (live). Either change them to 7497/7496 in the Gateway's API settings, or set `IBKR_PAPER_PORT` / `IBKR_LIVE_PORT` in `.env`.

---

## Running in Development

```bash
npm run dev
```

This starts three processes concurrently:

| Process | Command | Port |
|---|---|---|
| Python backend | `uv run uvicorn backend.main:app --reload` | 8000 |
| Vite dev server | `vite` | 5273 |
| Electron | waits for both ports, then launches | — |

React changes apply instantly via HMR. Python changes trigger a backend reload automatically. Open DevTools from the Electron window for frontend debugging.

You can also start services individually:

```bash
npm run dev:backend    # Python only
npm run dev:frontend   # Vite only
npm run dev:electron   # Electron only (assumes backend + Vite are already up)
```

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
- The renderer is served from the custom `app://bundle` scheme (not `file://`), which is the origin the backend's CORS policy allows.
- The backend runs with its working directory set to the user data folder, `~/Library/Application Support/ibkr-financial-advisor/`. A template `.env` is created there on first launch; the Anthropic API key entered in **Settings** is saved to it (owner-only permissions). The SQLite chat database lives there too.

The app is not code-signed; macOS may require right-click → **Open** the first time. An app icon can be added as `assets/icon.icns` (and referenced via `mac.icon` in `electron-builder.yml`).

---

## Project Structure

```
ibkr-financial-advisor/
│
├── electron/
│   ├── main.cjs          # Electron main process; spawns backend + serves app:// in prod
│   └── preload.cjs       # contextBridge API surface
│
├── backend/
│   ├── main.py           # FastAPI app + lifespan (DB init, IB cleanup)
│   ├── config.py         # Settings via pydantic-settings + .env
│   ├── database.py       # SQLite engine, ChatThread, ChatMessage models
│   ├── routers/
│   │   ├── connection.py # GET /status, POST /connect, POST /auto-connect
│   │   ├── portfolio.py  # GET /summary, /positions, /snapshot, /chart/:symbol
│   │   ├── chat.py       # REST thread CRUD + WS /ws/:thread_id streaming
│   │   └── settings.py   # AI provider selection, Anthropic key, OpenAI-compatible config
│   └── services/
│       ├── ibkr_service.py   # ib_insync singleton; connect, positions, bars
│       └── ai_service.py     # Anthropic / OpenAI-compatible streaming with portfolio system prompt
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
    │   └── useChat.ts        # Thread CRUD + WebSocket streaming state
    ├── components/
    │   ├── ConnectionGuard.tsx
    │   ├── Sidebar.tsx
    │   ├── Layout.tsx
    │   ├── ui/               # Shadcn primitives (button, card, badge, …)
    │   ├── dashboard/        # AccountSummary, PositionsTable, TradingChart
    │   └── chat/             # ChatSessionList, ChatWindow, MessageBubble
    └── pages/
        ├── Dashboard.tsx
        ├── Chat.tsx
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

---

## WebSocket Chat Protocol

**Client → Server**
```json
{ "message": "Should I rebalance my tech exposure?" }
```

**Server → Client**
```json
{ "type": "start" }
{ "type": "chunk", "content": "Based on your current " }
{ "type": "chunk", "content": "positions…" }
{ "type": "done" }
```

Error frame: `{ "type": "error", "content": "…" }`

---

## Notes

- **Paper vs Live** — the app only auto-connects to paper (`7497`). Connecting to live (`7496`) always takes an explicit click. Never use live credentials for testing.
- **API key security** — API keys live in `.env` (owner-only permissions) and are only read by the local Python process. The Settings screen can write a new key, but the backend never sends a stored key back to the renderer.
- **What leaves your machine** — portfolio data and chat history are stored locally. Each AI Advisor message sends the conversation plus a snapshot of your positions, P&L, and balances to the selected AI provider. With OpenRouter, the request also passes through OpenRouter to the model's provider; its privacy settings can restrict routing to providers that don't train on or retain data. A local model (Ollama, LM Studio) keeps everything on your machine.
- **Model IDs** — the OpenAI-compatible model must be an ID the endpoint lists (e.g. `vendor/model-name` on OpenRouter). OpenRouter lists models without checking the key, so a wrong OpenRouter key only shows up as an error on the first chat message.
- **Multiple IB clients** — if another app (e.g. the TWS API demo) is connected with `clientId=1`, change `IBKR_CLIENT_ID` in `.env` to avoid conflicts.
