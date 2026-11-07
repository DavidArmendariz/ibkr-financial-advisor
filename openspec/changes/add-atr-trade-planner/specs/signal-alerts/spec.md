# Spec Delta

## MODIFIED Requirements

### Requirement: Indicators
On each completed bar the system SHALL compute session VWAP (from 09:30 ET, or 04:00 ET when pre-market is included, through to 20:00 ET when extended hours are included) and the volume-weighted standard deviation of typical price around it, a fast and slow EMA (default 9 and 21), Bollinger Bands (default 20 periods, 2 standard deviations), Wilder's RSI (default 14 periods), Wilder's ATR (default 14 periods), and relative volume against the average of the previous bars (default 20).

#### Scenario: VWAP resets each session
- **WHEN** a new trading session starts
- **THEN** VWAP and its standard deviation restart from that session's first bar

#### Scenario: RSI with no losses
- **WHEN** every bar in the RSI period closed higher
- **THEN** RSI is 100

#### Scenario: After the close
- **WHEN** pre-market is included and a bar completes after the regular close
- **THEN** VWAP continues from that session's total, and it restarts at the next session

#### Scenario: Triggers stay in regular hours
- **WHEN** VWAP continues after the close
- **THEN** no signal is raised from it, because signals only fire inside regular hours

#### Scenario: ATR across a gap
- **WHEN** a session opens away from the previous close
- **THEN** the first bar's true range includes the gap from that close

### Requirement: Signals view
The Signals view SHALL show a live chart of the symbol's bars with VWAP, both EMAs, Bollinger Bands, volume, a volume profile, and a marker at each signal; an RSI pane under the chart; the IBKR connection, market data, and LLM filter status (including the IBKR error when market data is refused); current indicator values, including RSI and ATR; the recent signals; and the settings.

#### Scenario: Missing market data subscription
- **WHEN** IBKR refuses the real-time subscription
- **THEN** the market data status shows IBKR's error and the system retries every 5 minutes

#### Scenario: Forming bar
- **WHEN** streaming is active
- **THEN** the chart's latest candle updates every 5 seconds before the bar completes
