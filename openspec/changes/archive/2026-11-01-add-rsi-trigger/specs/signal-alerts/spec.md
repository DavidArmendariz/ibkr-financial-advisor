# Spec Delta

## ADDED Requirements

### Requirement: RSI trigger
The RSI trigger, in the technical category, SHALL raise an above signal when RSI crosses above the upper level (default 75), and a below signal when it crosses below the lower level (default 25). The levels and RSI period are editable in the Signals settings. One switch covers both directions, and a cross requires the previous RSI on the other side of the level within the same session.

#### Scenario: RSI crosses above the upper level
- **WHEN** the upper level is 75, the previous RSI was at or below 75, and this bar's RSI is above 75
- **THEN** an RSI above signal is raised

#### Scenario: RSI crosses below the lower level
- **WHEN** the lower level is 25, the previous RSI was at or above 25, and this bar's RSI is below 25
- **THEN** an RSI below signal is raised

#### Scenario: Staying beyond a level
- **WHEN** RSI stays beyond a level on the following bars
- **THEN** no further signal in that direction is raised until RSI has returned inside the level and crossed again

#### Scenario: Directions are separate
- **WHEN** an above signal fired and RSI crosses below the lower level within the cooldown
- **THEN** a below signal is raised, because each direction has its own cooldown

#### Scenario: Levels changed
- **WHEN** the user changes a level and saves
- **THEN** the next completed bar uses it, without a restart or a rebuild of the indicators

#### Scenario: Period changed
- **WHEN** the user changes the RSI period and saves
- **THEN** the indicators are rebuilt from history

#### Scenario: Independent of other triggers
- **WHEN** RSI crosses a level with low volume and no other cross
- **THEN** an RSI signal is raised

## MODIFIED Requirements

### Requirement: Indicators
On each completed bar the system SHALL compute session VWAP (from 09:30 ET, or 04:00 ET when pre-market is included) and the volume-weighted standard deviation of typical price around it, a fast and slow EMA (default 9 and 21), Bollinger Bands (default 20 periods, 2 standard deviations), Wilder's RSI (default 14 periods), and relative volume against the average of the previous bars (default 20).

#### Scenario: VWAP resets each session
- **WHEN** a new trading session starts
- **THEN** VWAP and its standard deviation restart from that session's first bar

#### Scenario: RSI with no losses
- **WHEN** every bar in the RSI period closed higher
- **THEN** RSI is 100

### Requirement: Trigger switches
The Signals settings SHALL group triggers into Volume and Technical categories, each trigger with an on/off switch. By default relative volume, EMA cross, VWAP band, and RSI are on and VWAP cross is off.

#### Scenario: First use
- **WHEN** the user has never changed the trigger switches
- **THEN** the Signals settings show relative volume, EMA cross, VWAP band, and RSI on and VWAP cross off, under their categories

#### Scenario: Switch applied live
- **WHEN** the user turns a trigger on or off and saves
- **THEN** the next completed bar uses the new switches, without a restart or a rebuild of the indicators

#### Scenario: Switches survive a restart
- **WHEN** the user changes a trigger switch and restarts the app
- **THEN** the switch keeps its saved state

#### Scenario: All triggers off
- **WHEN** the user turns every trigger off and saves
- **THEN** the save succeeds and no signals are raised

### Requirement: Desktop notifications
Each notified signal SHALL produce a native desktop notification titled with the symbol, trigger, and price, showing the trigger's category, key indicator values including RSI, and the LLM's reason. Notifications SHALL arrive while the app is running even if its window is closed. Clicking a notification SHALL open the Signals view.

#### Scenario: Window closed
- **WHEN** a signal fires while the app's window is closed but the app is still running
- **THEN** a desktop notification appears

#### Scenario: Different triggers
- **WHEN** a volume signal and an EMA cross signal fire
- **THEN** each has its own notification naming its trigger and category

### Requirement: Signals view
The Signals view SHALL show a live chart of the symbol's bars with VWAP, both EMAs, Bollinger Bands, volume, and a marker at each signal; the IBKR connection, market data, and LLM filter status (including the IBKR error when market data is refused); current indicator values, including RSI; the recent signals; and the settings.

#### Scenario: Missing market data subscription
- **WHEN** IBKR refuses the real-time subscription
- **THEN** the market data status shows IBKR's error and the system retries every 5 minutes

#### Scenario: Forming bar
- **WHEN** streaming is active
- **THEN** the chart's latest candle updates every 5 seconds before the bar completes

### Requirement: Signal History filter
The Signal History view SHALL let the user show all signals or only those from one trigger: relative volume, EMA cross, VWAP cross, VWAP band above, VWAP band below, RSI above, or RSI below.

#### Scenario: Filter by trigger
- **WHEN** the user selects EMA cross
- **THEN** only EMA cross signals are listed, and Load older continues within that filter

### Requirement: Live settings
Signal settings SHALL be editable in the Signals view, persisted locally, validated, and applied without restarting. Changing the timeframe or an indicator period SHALL rebuild the indicators from history.

#### Scenario: Invalid settings
- **WHEN** the user sets the fast EMA longer than the slow EMA
- **THEN** the save is rejected with an explanation

#### Scenario: RSI levels out of order
- **WHEN** the user sets the RSI lower level at or above the upper level
- **THEN** the save is rejected with an explanation
