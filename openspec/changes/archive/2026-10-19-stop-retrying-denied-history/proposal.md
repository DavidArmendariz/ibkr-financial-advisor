# Proposal

## Why

The account has no market data permission for CME's index feed, so every 5 minutes the Macro service asks IBKR for Dow Jones (INDU) bars, gets `Error 162 … No market data permissions for CME IND`, and logs it again. A missing subscription won't fix itself between retries, so the retries only fill the backend log with the same error and spend historical-data requests on a known refusal.

## What Changes

- When IBKR refuses an indicator's historical bars because the account lacks permission for that data (error 162 with "No market data permissions"), the Macro service stops requesting that indicator's bars.
- The card behaves as now: it shows the IBKR error when it has no other value, and the streamed quote (if any) keeps updating.
- The indicator's bars are requested again after the IBKR connection is re-established, including after switching between paper and live, since the permissions may differ.
- Other refusals (pacing violations, "no data" answers, streaming refusals) keep the existing 5-minute retry.

This change doesn't add IBKR requests, touch order handling or API keys, or send data off the machine. It only makes fewer historical-data requests; IBKR access stays read-only.

## Capabilities

### New Capabilities

### Modified Capabilities
- `macro-indicators`: "Errors and disconnection" no longer retries every 5 minutes when IBKR refuses historical data for lack of permissions; it retries after a reconnect instead.

## Impact

- `backend/macro/service.py`: a per-slot flag set from `_on_error`, checked before `_refresh_bars`, cleared in `_on_disconnected`.
- `tests/test_macro.py`: tests for the skip and the reset on reconnect.
- No API, renderer or dependency changes.
