# IBKR Financial Advisor

A local-first desktop application for trading and AI-powered financial advising, connected directly to Interactive Brokers via TWS or IB Gateway.

Built with Electron + React on the frontend and a Python FastAPI backend — everything runs on your machine, your data never leaves it.

---

## Features

**Dashboard**
- Real-time account summary: Net Liquidation Value, Unrealized P&L, Realized P&L, Buying Power
- Sortable positions table with ticker, asset class, quantity, average cost, market price, and P&L
- Interactive candlestick chart (TradingView `lightweight-charts`) with 1D / 5D / 1M / 3M timeframes; click any position row to load its chart

**AI Financial Advisor**
- Persistent chat sessions stored in a local SQLite database
- Each message automatically injects a live snapshot of your portfolio (positions, P&L, cash) into the system prompt
- Real-time streaming responses via WebSocket
- Session sidebar: create, switch between, and delete conversations

**TWS Connection Guard**
- On launch, auto-detects TWS / IB Gateway on `127.0.0.1:7497` (paper) or `7496` (live)
- Shows a lock screen with troubleshooting instructions until a connection is established
- Live connection indicator and Net Liquidation Value always visible in the sidebar footer

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | Electron 34 |
| Frontend | React 18, Vite 6, Tailwind CSS v4, Shadcn UI |
| IBKR connectivity | Python 3.12, `ib_insync` |
| API server | FastAPI, Uvicorn |
| AI | Anthropic Claude (streaming via `anthropic` SDK) |
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

Edit `.env` and fill in your values:

```env
ANTHROPIC_API_KEY=sk-ant-...
IBKR_PORT=7497          # 7497 = paper trading, 7496 = live
IBKR_CLIENT_ID=1
BACKEND_PORT=8000
```

### 5. Configure TWS / IB Gateway

In Trader Workstation:

1. **File → Global Configuration → API → Settings**
2. Enable **Enable ActiveX and Socket Clients**
3. Set **Socket port** to `7497` (paper) or `7496` (live)
4. Disable **Read-Only API** if you want order management later
5. Optionally add `127.0.0.1` to the trusted IP list

---

## Running in Development

```bash
npm run dev
```

This starts three processes concurrently:

| Process | Command | Port |
|---|---|---|
| Python backend | `uv run uvicorn backend.main:app --reload` | 8000 |
| Vite dev server | `vite` | 5173 |
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

### Step 1 — Freeze the Python backend

```bash
npm run package:backend
```

PyInstaller bundles the FastAPI server into a standalone binary at `backend-dist/server` (no Python installation needed on the target machine).

### Step 2 — Build the React app and package everything

```bash
npm run package:mac          # universal binary (arm64 + x64)
```

Output lands in `dist-electron/`. You'll find both a `.dmg` installer and a `.app` bundle.

### Test the packaged app

```bash
open "dist-electron/mac-universal/IBKR Financial Advisor.app"
```

Or mount the `.dmg` and drag to Applications as normal.

---

## Project Structure

```
ibkr-financial-advisor/
│
├── electron/
│   ├── main.cjs          # Electron main process; spawns backend in prod
│   └── preload.cjs       # contextBridge API surface
│
├── backend/
│   ├── main.py           # FastAPI app + lifespan (DB init, IB cleanup)
│   ├── config.py         # Settings via pydantic-settings + .env
│   ├── database.py       # SQLite engine, ChatThread, ChatMessage models
│   ├── routers/
│   │   ├── connection.py # GET /status, POST /connect, POST /auto-connect
│   │   ├── portfolio.py  # GET /summary, /positions, /snapshot, /chart/:symbol
│   │   └── chat.py       # REST thread CRUD + WS /ws/:thread_id streaming
│   └── services/
│       ├── ibkr_service.py   # ib_insync singleton; connect, positions, bars
│       └── ai_service.py     # Anthropic streaming with portfolio system prompt
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
        └── Chat.tsx
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/connection/status` | Current TWS connection state |
| `POST` | `/api/connection/auto-connect` | Try paper port, fall back to live |
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

- **Paper vs Live** — the app defaults to auto-connect (paper first). Paper trading port is `7497`, live is `7496`. Never use live credentials for testing.
- **API key security** — `ANTHROPIC_API_KEY` is read from `.env` by the local Python process only; it is never exposed to the Electron renderer.
- **No data leaves your machine** — all portfolio data, chat history, and AI context are processed and stored locally.
- **Multiple IB clients** — if another app (e.g. the TWS API demo) is connected with `clientId=1`, change `IBKR_CLIENT_ID` in `.env` to avoid conflicts.
