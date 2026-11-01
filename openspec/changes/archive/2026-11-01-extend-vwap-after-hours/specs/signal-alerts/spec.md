# Spec Delta

## MODIFIED Requirements

### Requirement: Indicators
On each completed bar the system SHALL compute session VWAP (from 09:30 ET, or 04:00 ET when pre-market is included, through to 20:00 ET when extended hours are included) and the volume-weighted standard deviation of typical price around it, a fast and slow EMA (default 9 and 21), Bollinger Bands (default 20 periods, 2 standard deviations), Wilder's RSI (default 14 periods), and relative volume against the average of the previous bars (default 20).

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
