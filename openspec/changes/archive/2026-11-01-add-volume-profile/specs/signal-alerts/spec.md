# Spec Delta

## ADDED Requirements

### Requirement: Volume profile
The Signals chart SHALL show a volume profile for the latest regular session that has bars: horizontal bars along the chart's right edge showing the volume traded at each price, positioned on the chart's price scale.

#### Scenario: During the session
- **WHEN** a bar completes during regular hours
- **THEN** the profile includes that bar

#### Scenario: Before the open
- **WHEN** today's regular session hasn't started
- **THEN** the bars show yesterday's session

#### Scenario: Pre-market and after-hours
- **WHEN** bars fall outside regular hours
- **THEN** they aren't counted, even when pre-market is included in VWAP

#### Scenario: Zoom
- **WHEN** the user zooms or pans the chart
- **THEN** the bars stay aligned with their prices

#### Scenario: Estimated from bars
- **WHEN** a bar spans several price levels
- **THEN** its volume is spread evenly across them, because bars don't say which price each trade happened at

### Requirement: Volume profile levels
The chart SHALL show lines for the session's Point of Control, the price with the most volume, and its value area, the range around it holding 70% of the session's volume. Yesterday's levels SHALL show as muted lines, whenever that session's data is available.

#### Scenario: Levels during the session
- **WHEN** the session has bars
- **THEN** the chart labels today's POC, value area high, and value area low

#### Scenario: Yesterday's levels
- **WHEN** today's session is under way
- **THEN** yesterday's levels show as muted lines, complete even if the chart no longer holds all of that session's bars

#### Scenario: Value area growth
- **WHEN** the value area is built
- **THEN** it starts at the POC and adds the busier neighboring price level until it holds 70% of the volume

### Requirement: Volume profile toggle
The chart SHALL offer a toggle that shows or hides the volume profile and its lines. It SHALL be on by default and remembered between launches.

#### Scenario: Hide the profile
- **WHEN** the user turns the toggle off
- **THEN** the bars and lines disappear, and the rest of the chart stays the same

#### Scenario: Remembered
- **WHEN** the user turns it off and reopens the app
- **THEN** it stays off

### Requirement: Volume profile is context only
The volume profile SHALL NOT raise signals or change any trigger.

#### Scenario: Price reaches a level
- **WHEN** price crosses the POC
- **THEN** no alert is raised

## MODIFIED Requirements

### Requirement: Signals view
The Signals view SHALL show a live chart of the symbol's bars with VWAP, both EMAs, Bollinger Bands, volume, a volume profile, and a marker at each signal; an RSI pane under the chart; the IBKR connection, market data, and LLM filter status (including the IBKR error when market data is refused); current indicator values, including RSI; the recent signals; and the settings.

#### Scenario: Missing market data subscription
- **WHEN** IBKR refuses the real-time subscription
- **THEN** the market data status shows IBKR's error and the system retries every 5 minutes

#### Scenario: Forming bar
- **WHEN** streaming is active
- **THEN** the chart's latest candle updates every 5 seconds before the bar completes
