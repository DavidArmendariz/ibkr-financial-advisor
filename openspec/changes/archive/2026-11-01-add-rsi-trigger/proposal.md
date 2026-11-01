# Proposal

## Why

The user wants an alert when momentum reaches an extreme. RSI (Relative Strength Index) is the standard measure for this, and none of the current triggers use it.

## What Changes

- Add an **RSI** technical trigger with one switch and separate alerts in each direction. It fires when RSI crosses above the upper level or below the lower level.
- Add settings for the upper level (default 75), lower level (default 25), and RSI period (default 14), all editable in the Signals settings.
- The trigger is on by default, because the user asked for this alert.
- Show RSI on the Signals view's live values, in alert notifications, and in the saved signal.
- Add RSI above and RSI below filters to Signal History, and chart markers.
- Pre-mortems and post-mortems work on the new signals, judged in both directions, because an RSI extreme doesn't imply a direction.
- On the last 180 sessions, the defaults add about 3 alerts per session, for about 17 in total at the current 3x volume threshold.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: adds the RSI trigger, adds RSI to the computed indicators, and updates the trigger switches, notifications, live values, and history filter.

- `signal-analysis`: the post-mortem verdict requirement adds RSI signals to those judged in both directions.

## Impact

- **IBKR access:** unchanged. RSI is computed from the same bars, with no new requests.
- **Order handling:** not touched. It's an alert only.
- **API keys:** not touched.
- **Data leaving the machine:** the LLM filter stays off by default. When on, and in analyses, the snapshot gains the RSI value.
- **Code:** `backend/signals/indicators.py`, `models.py`, `rules.py`, `config.py`, `electron/signal-notifications.cjs`, `src/components/signals/SignalSettingsForm.tsx`, `SignalChart.tsx`, `LiveValues.tsx`, `SignalTable.tsx`, `src/pages/SignalHistory.tsx`, `src/types/index.ts`, `tests/`, `README.md`.
- **Settings:** adds `SIGNALS_TRIGGER_RSI_ENABLED`, `SIGNALS_RSI_PERIOD`, `SIGNALS_RSI_UPPER`, and `SIGNALS_RSI_LOWER` to `.env`.
