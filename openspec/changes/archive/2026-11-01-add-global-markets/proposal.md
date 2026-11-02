# Proposal

## Why

SOXL trades on chip sentiment that often forms overnight, while Korea, Japan, and Europe are open. The app only shows US markets, so the user has to look elsewhere to see how those markets and their chip stocks moved before the US open.

## What Changes

- A new **Asia & Europe** sidebar item, directly below Macro.
- Index cards for the Nikkei 225, KOSPI 200, AEX (ASML's home index), and Euro Stoxx 50.
- Chip stock cards: Samsung, SK Hynix, TSMC, Tokyo Electron, Advantest, Disco, Renesas, ASML, ASM International, BE Semiconductor, Infineon, and STMicroelectronics.
- Each card shows the last value in local currency, the change since the previous close, an intraday sparkline, whether the market is open, and the local time of the latest data.
- Macro, signals, and every other feature stay as they are.

## Capabilities

### New Capabilities

- `global-markets`: the Asia & Europe view, its instruments, and how their data is refreshed and shown.

### Modified Capabilities

None.

## Impact

- **IBKR access:** read-only. Adds historical bar requests and contract details on the shared connection. It opens no market data lines and doesn't call `reqMarketDataType`, so other features aren't affected.
- **Order handling:** not touched. Nothing places, changes, or cancels orders.
- **API keys:** not touched.
- **Data leaving the machine:** none. No AI provider or third-party source is used.
- **Code:** new `backend/global_markets/`, a new router, `backend/main.py`, a new page, hook, and components, `Sidebar.tsx`, `Layout.tsx`, `src/types/index.ts`, `src/lib/api.ts`, README, and `CLAUDE.md`.
