# Proposal

## Why

RSI shows as a single live number, so there's no way to see how it got there or how close it came to the alert levels. Seeing it under the price chart makes RSI alerts easier to judge against the candles.

## What Changes

- Add an RSI pane directly under the Signals chart, with a line on a fixed 0–100 scale.
- Show the upper and lower alert levels as dashed lines that follow the settings.
- Keep the pane aligned with the price chart: panning, zooming, and the crosshair stay in sync.
- Show the RSI value and period in the pane's legend, for the hovered bar or the latest one.
- RSI updates when each bar completes, so it doesn't move with the forming candle.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: the Signals view gains an RSI pane under the chart.

## Impact

- **IBKR access:** unchanged. The chart data already includes RSI for every bar.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none.
- **Code:** `src/components/signals/SignalChart.tsx` and `README.md`. The backend and API don't change.
