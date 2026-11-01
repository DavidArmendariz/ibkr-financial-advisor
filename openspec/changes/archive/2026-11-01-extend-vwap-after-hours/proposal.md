# Proposal

## Why

The Signals chart's VWAP line stops at the 16:00 ET close, and the user wants it to continue through after-hours.

## What Changes

- When pre-market is included, session VWAP and its standard deviation continue through after-hours to 20:00 ET, then restart at the next session.
- With regular-hours data only, nothing changes, because no after-hours bars arrive.
- Signals are unaffected: triggers still fire only inside regular hours, and regular-hours VWAP values don't change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: the indicators requirement extends VWAP through after-hours when extended hours are included.

## Impact

- **IBKR access:** unchanged. These bars are already received.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none. LLM snapshots only exist for signals, which stay in regular hours.
- **Code:** `backend/signals/sessions.py`, `README.md`, tests.
