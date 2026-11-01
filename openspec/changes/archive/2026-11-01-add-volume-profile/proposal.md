# Proposal

## Why

The Signals chart shows when SOXL traded, but not at which prices. A volume profile shows where trading concentrated, which gives objective reference levels for reading alerts.

## What Changes

- Add a volume profile to the Signals chart for the current regular session: faint horizontal bars along the chart's right edge.
- Add lines for today's Point of Control (POC), value area high, and value area low.
- Add yesterday's POC, value area high, and value area low as muted reference lines. Before the open, the bars show yesterday's session.
- Add a Volume profile toggle in the chart's legend, on by default and remembered between launches.
- The profile updates as each bar completes, and follows zoom and panning.
- It's context only: no new alerts, and the triggers don't change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: the Signals view gains a volume profile on the chart.

## Impact

- **IBKR access:** unchanged. The profile comes from the bars the app already receives, with no new requests or market data lines.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none.
- **Code:** new `backend/signals/volume_profile.py`, `backend/signals/pipeline.py`, `backend/signals/service.py`, new `src/components/signals/volumeProfilePrimitive.ts`, `src/components/signals/SignalChart.tsx`, `src/types/index.ts`, `README.md`, new backend tests.
- **API:** the signals `live` update and `/api/signals/state` gain a `volume_profile` field.
