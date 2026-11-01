# Proposal

## Why

The app has seven signal types, and the backtests found no proven edge. There's no way to see how alerts actually played out except by running a post-mortem on one signal at a time. The user needs measured results per trigger to decide which alerts deserve attention.

## What Changes

- For every recorded signal, the system measures SOXL's move 5, 15, and 30 minutes later, plus the largest move up and down within those 30 minutes.
- Signals already in the history are measured too, as far back as IBKR still has 1-minute bars.
- Signal History gets a results table per trigger: sample size, average and median move, share of moves up, and average largest moves.
- The table includes a baseline row, the same measurements from every regular-hours minute on the same days, so a trigger can be compared with no signal at all.
- Each signal's own figures show in its details.
- Triggers, notifications, the LLM filter, and post-mortems don't change. No AI provider is involved.

## Capabilities

### New Capabilities

- `signal-outcomes`: measuring what happened after each signal, and reporting the results per trigger against a baseline.

### Modified Capabilities

None.

## Impact

- **IBKR access:** read-only. Adds historical 1-minute bar requests through the existing `get_historical_bars`, limited to one per pass, plus a confirming request after an empty reply.
- **Order handling:** not touched. Nothing places, changes, or cancels orders.
- **API keys:** not touched.
- **Data leaving the machine:** none. Figures are computed and stored locally, and no provider is called.
- **Code:** new `backend/signals/outcomes.py`, new tables in `backend/database.py`, `backend/signals/service.py`, `backend/routers/signals.py`, `src/pages/SignalHistory.tsx`, the signal details, a new results component, `src/types/index.ts`, `src/lib/api`, README, and `CLAUDE.md`'s capability list.
