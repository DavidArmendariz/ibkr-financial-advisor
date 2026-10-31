# Proposal

## Why

The backtest on 180 SOXL sessions found no proven edge from requiring a VWAP cross, EMA trend, and high volume together. The user wants each event as its own alert, to judge it separately, and to switch each one on or off without changing code.

## What Changes

- **BREAKING:** replace the single LONG entry rule, which required all conditions at once, with independent triggers. Each trigger that is on raises its own alert, and nothing is ANDed.
- Group triggers by category in the Signals settings, where each has an on/off switch:
  - **Volume triggers:** Relative volume (on by default).
  - **Technical triggers:** EMA cross (on by default) and VWAP cross (off by default).
- Each alert names its trigger and category in its notification and in signal history. If two triggers fire on one bar, the user gets two alerts.
- The relative volume threshold stays editable in the Signals settings, with its default unchanged at 1.5×.
- Switches apply live, with no restart, and persist. All triggers can be off, which means no alerts.
- **Expect many more alerts.** On the last 180 sessions, the defaults give about 34 alerts per session (26 volume, 8 EMA), against about 0.6 today. Turning VWAP on adds about 4. Raising the volume threshold reduces this: 3× gives about 4 volume alerts per session.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: replaces the long entry rule with independent, categorized triggers, and updates notifications to name the trigger and category.

## Impact

- **IBKR access:** unchanged. The same bars and indicators are used, and no new requests are made.
- **Order handling:** not touched. Signals remain alerts only.
- **API keys:** not touched.
- **Data leaving the machine:** the LLM filter stays off by default. When on, it runs once per alert, so more alerts mean more calls to the configured provider, each with the same kind of snapshot plus the trigger's category.
- **Code:** `backend/signals/config.py`, `rules.py`, `pipeline.py`, `service.py`, `electron/signal-notifications.cjs`, `src/components/signals/SignalSettingsForm.tsx`, `SignalTable.tsx`, `SignalChart.tsx`, `src/types/index.ts`, `tests/test_rules.py`, `README.md`.
- **Settings:** adds `SIGNALS_TRIGGER_VOLUME_ENABLED`, `SIGNALS_TRIGGER_EMA_ENABLED`, and `SIGNALS_TRIGGER_VWAP_ENABLED` to `.env`.
