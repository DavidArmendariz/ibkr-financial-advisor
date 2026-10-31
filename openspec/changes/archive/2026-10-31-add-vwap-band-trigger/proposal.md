# Proposal

## Why

The VWAP cross only says price moved above VWAP. The user also wants to know when price has stretched unusually far above or below it, measured in standard deviations they can set.

## What Changes

- Add a **VWAP band** technical trigger with one switch and separate alerts for each direction. It fires when the close crosses above VWAP plus N standard deviations, or below VWAP minus N standard deviations.
- Each direction has its own notification and cooldown.
- Add a setting for N, editable in the Signals settings and applied live, with a default of 2.
- The trigger is on by default, because the user asked for this notification.
- Standard deviation means the standard VWAP bands measure: the volume-weighted spread of typical price around the session's VWAP, restarting each session.
- Add VWAP band above and VWAP band below filters to Signal History.
- On the last 180 sessions, the default adds about 2.1 alerts per session across both directions, for about 36 in total. N of 1 gives about 8.9, 1.5 gives 6.1, 2.5 gives 0.4, and 3 almost never fires.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: adds the VWAP band trigger, adds its standard deviation to the computed indicators, and updates the trigger switches and history filter.

## Impact

- **IBKR access:** unchanged. The trigger uses the same bars, with no new requests.
- **Order handling:** not touched. It's an alert only.
- **API keys:** not touched.
- **Data leaving the machine:** the LLM filter stays off by default. When on, it runs once per alert, and the snapshot gains the VWAP standard deviation.
- **Code:** `backend/signals/indicators.py`, `models.py`, `rules.py`, `pipeline.py`, `config.py`, `src/components/signals/SignalSettingsForm.tsx`, `SignalChart.tsx`, `src/pages/SignalHistory.tsx`, `src/types/index.ts`, `tests/`, `README.md`.
- **Settings:** adds `SIGNALS_TRIGGER_VWAP_BAND_ENABLED` and `SIGNALS_VWAP_BAND_STD` to `.env`.
