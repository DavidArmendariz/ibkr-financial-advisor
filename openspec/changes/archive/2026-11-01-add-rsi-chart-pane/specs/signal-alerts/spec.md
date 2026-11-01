# Spec Delta

## ADDED Requirements

### Requirement: RSI chart pane
The Signals view SHALL show an RSI pane directly under the chart, with the RSI line on a fixed 0 to 100 scale, the upper and lower alert levels as dashed lines, and the RSI period and value for the hovered bar or the latest one.

#### Scenario: Levels follow the settings
- **WHEN** the user saves new RSI levels
- **THEN** the dashed lines move to the new levels without a reload

#### Scenario: New bar
- **WHEN** a bar completes while streaming
- **THEN** the RSI line extends to that bar

#### Scenario: Warmup bars
- **WHEN** the first bars have no RSI yet
- **THEN** the line starts at the first bar that has one, and the pane stays aligned with the chart

### Requirement: RSI pane stays in sync
The RSI pane and the price chart SHALL show the same bars in the same horizontal positions. Panning or zooming either one SHALL move both, and the crosshair SHALL show on both.

#### Scenario: Zoom the price chart
- **WHEN** the user zooms or pans the price chart
- **THEN** the RSI pane shows the same bars

#### Scenario: Zoom the RSI pane
- **WHEN** the user zooms or pans the RSI pane
- **THEN** the price chart shows the same bars

#### Scenario: Hover
- **WHEN** the user hovers over a bar on either one
- **THEN** both show the crosshair at that bar, and the legends show that bar's values

#### Scenario: Forming bar
- **WHEN** a bar is still forming
- **THEN** the candle updates, the RSI line waits for the bar to complete, and the bars stay aligned

## MODIFIED Requirements

### Requirement: Signals view
The Signals view SHALL show a live chart of the symbol's bars with VWAP, both EMAs, Bollinger Bands, volume, and a marker at each signal; an RSI pane under the chart; the IBKR connection, market data, and LLM filter status (including the IBKR error when market data is refused); current indicator values, including RSI; the recent signals; and the settings.

#### Scenario: Missing market data subscription
- **WHEN** IBKR refuses the real-time subscription
- **THEN** the market data status shows IBKR's error and the system retries every 5 minutes

#### Scenario: Forming bar
- **WHEN** streaming is active
- **THEN** the chart's latest candle updates every 5 seconds before the bar completes
