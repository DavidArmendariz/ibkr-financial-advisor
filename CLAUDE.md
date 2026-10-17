# DeltaAdvisor

Local-first macOS desktop app (Electron + React) with a Python FastAPI backend, connected to Interactive Brokers through TWS / IB Gateway. Features: portfolio dashboard, AI Advisor chat, SOXL real-time signal alerts, SOXL gamma exposure. **It never places orders.**

## How changes are made: OpenSpec

Behavior is specified in `openspec/specs/<capability>/spec.md` (ibkr-connection, portfolio-dashboard, ai-advisor, ai-provider-settings, signal-alerts, gamma-exposure, app-lifecycle). These are the source of truth for what the app does.

For any new feature or behavior change, use the OpenSpec workflow instead of editing code directly:

1. `/opsx:propose <idea>` creates `openspec/changes/<name>/` with `proposal.md`, delta specs, `design.md` (decisions, with the alternatives considered) and `tasks.md`. Get the user's approval before implementing.
2. `/opsx:apply` implements the tasks.
3. `/opsx:archive` merges the delta specs into `openspec/specs/` and moves the change to `openspec/changes/archive/`.

Small bug fixes that don't change specified behavior can skip the workflow. The CLI is a pinned dev dependency: run it as `npx openspec …`. Validate with `npx openspec validate <change-name> --strict` or `npx openspec validate --specs --strict` (without an argument it prompts interactively). Project context and per-artifact rules are in `openspec/config.yaml`.

Decisions made before OpenSpec are in [docs/decisions.md](docs/decisions.md); new decisions belong in each change's `design.md`. User-facing setup and API reference live in README.md.

## Layout

- `electron/` — main process (`main.cjs`: spawns the packaged backend, quit/crash handling, dev Dock icon), `preload.cjs` (contextBridge), `signal-notifications.cjs` (native notifications from the signals WebSocket).
- `backend/` — FastAPI app. `services/ibkr_service.py` holds the single shared `ib_async` connection and the reconnect supervisor. `signals/` (pipeline, indicators, rules, LLM filter, replay CLI), `gamma/` (exposure calc + chain fetching), `routers/` (one per feature), `database.py` (SQLModel tables).
- `src/` — React 18 renderer. Views are `pages/*.tsx`, switched in `components/Layout.tsx` via the `AppTab` union in `types/index.ts` and the list in `components/Sidebar.tsx`. Each feature has a `hooks/use*.ts` and components under `components/<feature>/`.
- `tests/` — pytest suite (backend only).

## Commands

Node comes from nvm. On the WSL machine `~/.zshenv` puts nvm's default Node on PATH for non-interactive shells; if `node` isn't found elsewhere, prefix with `export PATH="$HOME/.nvm/versions/node/v24.14.0/bin:$PATH"`.

```bash
npm run dev                       # backend :8000 + Vite :5273 + Electron (predev kills a stale backend)
uv run pytest                     # backend tests
npx tsc --noEmit -p .             # frontend typecheck
npx vite build                    # frontend build
uv run python -m backend.signals.replay --date YYYY-MM-DD [--llm]   # replay a session through the signal rules
npx playwright install chromium   # once per machine: headless browser for UI checks
npm run package:backend && npm run build && npx electron-builder --mac --dir   # local .app build
```

Before calling work done: pytest, tsc and vite build pass, and UI changes are looked at in a browser. The renderer runs fine in Chrome at http://localhost:5273 (CORS allows it); clicks right after load can be swallowed while the app auto-connects, so wait a few seconds or click twice. For automated checks, drive it with Playwright (`require('@playwright/test').chromium` from a `node` script, run from the repo root so it resolves): locate controls by role/label and wait on them rather than sleeping, and keep scripts and screenshots in the scratchpad. Each launch gets a fresh `localStorage`, so it doesn't disturb the user's own browser state. macOS-only behavior (traffic lights, window dragging, Dock, notifications) still needs a check on the Mac.

## Conventions

- Comments explain *why*, sparingly. No docstrings. Match the surrounding style.
- Settings are persisted to `.env` with `backend.config.save_env_values` (owner-only file), one prefix per feature (`SIGNALS_*`, `GAMMA_*`), and applied live without a restart.
- API keys stay in the backend. The renderer only ever sees "set / …abcd hint". All LLM calls happen in the backend.
- IBKR access is read-only (`readonly=True`). Never add order placement.
- Auto-connect only ever targets the **paper** port; live always needs an explicit click.
- Time math is in US/Eastern via `zoneinfo` (`backend/signals/sessions.py: ET`). Trading hours come from IBKR `liquidHours` (handles half-days).
- Charts: palette and mark rules from the dataviz skill; series colors are the validated dark-mode categorical slots (`#3987e5`, `#d95926`, `#199e70`, `#c98500`, …).
- Commits: one commit per feature or fix, imperative subject, body explains why. Don't commit or push unless asked.

## IBKR gotchas (all hit in practice)

- **Real-time market data needs paid, API-eligible subscriptions** on the live account, shared to paper. SOXL stock bars need *NYSE American, BATS, ARCA, IEX… (Network B)*; options need *OPRA*. The free "US Real-Time Non Consolidated Streaming Quotes" feed does not work through the API (errors 420 / 10089 / 10168 / 354).
- **Competing live session**: if the live user is logged in elsewhere (IBKR mobile app, Client Portal), the paper session gets no market data (10197, "connected from a different IP address"). Log out of the phone app.
- After TWS restarts it may wait on the **paper trading disclaimer** (10141) and refuse API connections until someone clicks it.
- **Option open interest only arrives while the market is open**; after hours ~1 in 8 contracts report it. The gamma service caches OI in SQLite (`OptionOpenInterest`).
- Max ~100 simultaneous market data lines: batch option requests (gamma uses 80).
- The gamma service calls `reqMarketDataType(2)` (frozen) on the shared connection; that also affects other `reqMktData` users.
- Error 322 (too many account summary requests) shows up from the Dashboard's 15 s polling; `accountSummaryAsync` / `reqPositionsAsync` have no timeout.
- One-off scripts must use their own client ID (the app uses `IBKR_CLIENT_ID`, default 1; replay uses +50).

## Dev gotchas

- uvicorn shutdown can stall on "Waiting for background tasks"; it's capped with `--timeout-graceful-shutdown 5` (dev) / `timeout_graceful_shutdown=5` (packaged). A dev backend started before that flag existed needs its worker killed.
- React StrictMode mounts effects twice in dev: WebSockets open and immediately close once.
- Markdown components in the chat must stay module-level constants, or charts remount (and refetch) on every keystroke.
- Electron 34 ships Node 20, which has no global `WebSocket`; the main process uses the `ws` package.
- Closing the window keeps the app (and notifications) running in the Dock; Cmd+Q quits.
