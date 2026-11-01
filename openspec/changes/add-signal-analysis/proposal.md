# Proposal

## Why

The LLM filter gives a 25-word verdict in 5 seconds, before anyone knows how a signal played out. The user wants to study signals afterwards: first as if it were that moment, then with hindsight, to learn which alerts were worth taking.

## What Changes

- Add two on-demand buttons to each row in Signal History:
  - **Pre-mortem:** analyzes the signal using only what was known when it fired, and says whether to take it, what could go wrong, and what would prove it wrong.
  - **Post-mortem:** uses what happened afterwards, including measured outcomes, to judge whether taking it was a good idea.
- The pre-mortem never receives bars from after the signal, and the post-mortem states that it's written with hindsight.
- Results are saved, shown under the row, and can be run again.
- Analyses run only when the user clicks. Nothing runs automatically, and notifications and the LLM filter are unaffected.
- The configured AI provider does the analysis. The backend computes every number the post-mortem uses, so the model doesn't calculate outcomes.

## Capabilities

### New Capabilities

- `signal-analysis`: on-demand pre-mortem and post-mortem analysis of recorded signals, with saved results.

### Modified Capabilities

None. Signal History gains row actions, covered by the new capability, and its existing requirements don't change.

## Impact

- **IBKR access:** adds read-only historical bar requests for the signal's session, one per click. The connection stays `readonly=True`.
- **Order handling:** not touched. An analysis can say a signal was worth taking, but the app places nothing.
- **API keys:** stay in the backend. All LLM calls happen there, and the renderer never sees a key.
- **Data leaving the machine:** each click sends that signal's snapshot, session bars, and outcome figures to the provider configured in Settings. No positions, orders, balances, or account data are sent.
- **Code:** `backend/signals/llm_filter.py`, new `backend/signals/analysis.py`, `backend/signals/service.py`, `backend/routers/signals.py`, `backend/database.py`, `backend/services/ibkr_service.py`, `src/lib/api.ts`, `src/types/index.ts`, `src/components/signals/SignalTable.tsx`, new `src/components/signals/SignalAnalysisPanel.tsx`, `src/pages/SignalHistory.tsx`, `README.md`, new backend tests.
- **Database:** adds a `SignalAnalysis` table, created automatically.
