# signal-alerts Specification

## Purpose

Watches SOXL in real time and alerts the user through independent volume and technical triggers, each of which can be switched on or off, optionally screened by the configured AI provider. Alerts only; no orders are placed.

## Requirements

### Requirement: Real-time bars
The system SHALL build bars of the configured timeframe (1, 2, 3, 5, 10, 15, or 30 minutes; default 1) from IBKR's 5-second real-time bars, aligned to clock time, and SHALL warm up its indicators from IBKR history on start. Bars with missing 5-second data SHALL be discarded rather than emitted partially.

#### Scenario: Aggregated bars match IBKR history
- **WHEN** a full minute of 5-second bars is received
- **THEN** the resulting 1-minute bar has the same open, high, low, close, and volume as IBKR's 1-minute history for that minute

#### Scenario: Subscription starts mid-minute
- **WHEN** streaming begins partway through a bar
- **THEN** that incomplete bar is not used

### Requirement: Indicators
On each completed bar the system SHALL compute session VWAP (from 09:30 ET, or 04:00 ET when pre-market is included) and the volume-weighted standard deviation of typical price around it, a fast and slow EMA (default 9 and 21), Bollinger Bands (default 20 periods, 2 standard deviations), Wilder's RSI (default 14 periods), and relative volume against the average of the previous bars (default 20).

#### Scenario: VWAP resets each session
- **WHEN** a new trading session starts
- **THEN** VWAP and its standard deviation restart from that session's first bar

#### Scenario: RSI with no losses
- **WHEN** every bar in the RSI period closed higher
- **THEN** RSI is 100

### Requirement: Independent signal triggers
The system SHALL evaluate each trigger that is on, independently, on every completed bar, and SHALL raise a separate signal for each one that fires. No trigger SHALL depend on another trigger.

#### Scenario: Two triggers on one bar
- **WHEN** the fast EMA crosses above the slow EMA on a bar where relative volume is also above the threshold
- **THEN** two signals are raised, one for each trigger

#### Scenario: EMA cross on low volume
- **WHEN** the fast EMA crosses above the slow EMA and relative volume is below the threshold
- **THEN** an EMA cross signal is raised and no volume signal

#### Scenario: High volume without a cross
- **WHEN** relative volume is above the threshold and no cross happens
- **THEN** a volume signal is raised and no technical signal

### Requirement: Relative volume trigger
The relative volume trigger, in the volume category, SHALL fire on a completed bar whose relative volume exceeds the threshold (default 1.5×). The threshold SHALL be editable in the Signals settings. The signal carries no direction.

#### Scenario: Threshold changed
- **WHEN** the user sets the threshold to 3 and a bar's relative volume is 2.0
- **THEN** no volume signal is raised

### Requirement: EMA cross trigger
The EMA cross trigger, in the technical category, SHALL fire on the bar where the fast EMA crosses above the slow EMA. A cross requires the fast EMA at or below the slow EMA on the previous bar of the same session.

#### Scenario: EMA already above
- **WHEN** the fast EMA stays above the slow EMA without crossing on that bar
- **THEN** no EMA cross signal is raised

#### Scenario: Cross below VWAP
- **WHEN** the fast EMA crosses above the slow EMA while the close is below VWAP
- **THEN** an EMA cross signal is raised

### Requirement: VWAP cross trigger
The VWAP cross trigger, in the technical category, SHALL fire on the bar whose close crosses above VWAP. A cross requires the previous close at or below VWAP within the same session.

#### Scenario: Cross on low volume
- **WHEN** the VWAP cross trigger is on and the close crosses above VWAP while the fast EMA is below the slow EMA and relative volume is low
- **THEN** a VWAP cross signal is raised

### Requirement: VWAP band trigger
The VWAP band trigger, in the technical category, SHALL raise an above signal when the close crosses above session VWAP plus N standard deviations, and a below signal when it crosses below VWAP minus N standard deviations. N is editable in the Signals settings (default 2). One switch covers both directions, and a cross requires the previous close on the other side of its band within the same session.

#### Scenario: Close crosses above the band
- **WHEN** N is 2, the previous close was at or below its band, and this bar closes above VWAP plus 2 standard deviations
- **THEN** a VWAP band above signal is raised

#### Scenario: Close crosses below the band
- **WHEN** N is 2, the previous close was at or above its lower band, and this bar closes below VWAP minus 2 standard deviations
- **THEN** a VWAP band below signal is raised

#### Scenario: Staying beyond the band
- **WHEN** the close stays beyond a band on the following bars
- **THEN** no further signal in that direction is raised until the close has returned inside the band and crossed again

#### Scenario: Directions are separate
- **WHEN** an above signal fired and the close crosses below the lower band within the cooldown
- **THEN** a below signal is raised, because each direction has its own cooldown

#### Scenario: Setting changed
- **WHEN** the user changes N to 3 and saves
- **THEN** the next completed bar uses 3, without a restart or a rebuild of the indicators

#### Scenario: No spread yet
- **WHEN** the session's standard deviation is zero
- **THEN** no VWAP band signal is raised in either direction

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

### Requirement: Blackout windows and cooldown
The system SHALL NOT raise signals during the first or last N minutes of the regular session (default 10 each, using IBKR's actual trading hours so early closes are respected), outside regular hours, or within the cooldown after the previous signal of the same type (default 5 minutes).

#### Scenario: Early in the session
- **WHEN** a qualifying cross happens at 09:35 ET with a 10-minute open blackout
- **THEN** no signal is raised

### Requirement: Optional LLM filter
When enabled, each signal SHALL be judged by the AI provider configured in Settings using a snapshot of the signal (price, indicator values, last 20 bars). The provider SHALL return take or skip, a confidence from 0 to 1, and a reason of at most 25 words; it never computes indicators.

#### Scenario: Filter disabled
- **WHEN** the LLM filter is off
- **THEN** every signal is notified and marked unfiltered

### Requirement: LLM filter outcome
Only signals the provider takes at or above the confidence threshold (default 0.6) SHALL be notified. On a timeout of 5 seconds, an invalid reply, a provider error, or no configured provider, the signal SHALL be notified and marked unfiltered.

#### Scenario: Provider unavailable
- **WHEN** the LLM filter is on and the provider times out
- **THEN** the user is still notified and the signal is marked unfiltered

#### Scenario: Low-confidence take
- **WHEN** the provider answers take with confidence 0.4 and the threshold is 0.6
- **THEN** the signal is recorded but no notification is shown

### Requirement: Desktop notifications
Each notified signal SHALL produce a native desktop notification titled with the symbol, trigger, and price, showing the trigger's category, key indicator values including RSI, and the LLM's reason. Notifications SHALL arrive while the app is running even if its window is closed. Clicking a notification SHALL open the Signals view.

#### Scenario: Window closed
- **WHEN** a signal fires while the app's window is closed but the app is still running
- **THEN** a desktop notification appears

#### Scenario: Different triggers
- **WHEN** a volume signal and an EMA cross signal fire
- **THEN** each has its own notification naming its trigger and category

### Requirement: Signal history
Every signal SHALL be recorded locally, including ones the LLM filter skipped, with its trigger, category, snapshot, LLM decision, and whether it was notified. The Signals view SHALL show the latest 50, and they SHALL survive restarts.

#### Scenario: After restart
- **WHEN** the app restarts
- **THEN** previously recorded signals still appear in the Signals view

#### Scenario: Trigger shown
- **WHEN** the Signals view lists a signal
- **THEN** it shows the signal's trigger and category

### Requirement: Signals view
The Signals view SHALL show a live chart of the symbol's bars with VWAP, both EMAs, Bollinger Bands, volume, and a marker at each signal; an RSI pane under the chart; the IBKR connection, market data, and LLM filter status (including the IBKR error when market data is refused); current indicator values, including RSI; the recent signals; and the settings.

#### Scenario: Missing market data subscription
- **WHEN** IBKR refuses the real-time subscription
- **THEN** the market data status shows IBKR's error and the system retries every 5 minutes

#### Scenario: Forming bar
- **WHEN** streaming is active
- **THEN** the chart's latest candle updates every 5 seconds before the bar completes

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

### Requirement: Signal History view
The sidebar SHALL list a Signal History item, directly below Signals, that opens a view of every recorded signal, newest first, showing time, trigger, category, price, indicator values, LLM decision, and whether it was notified.

#### Scenario: Open the view
- **WHEN** the user clicks Signal History in the sidebar
- **THEN** the view opens with the newest signals first, and the Signal History item is shown as selected

#### Scenario: No signals recorded
- **WHEN** no signals have been recorded
- **THEN** the view says so

#### Scenario: Signals skipped by the LLM filter
- **WHEN** the LLM filter skipped a signal
- **THEN** it is listed and shown as not notified

#### Scenario: Not connected to IBKR
- **WHEN** the IBKR connection drops while the view is open
- **THEN** recorded signals still show until the connection lock screen takes over

### Requirement: Signal History paging
The Signal History view SHALL show up to 100 signals at first and let the user load 100 older signals at a time until none remain, without listing a signal twice or skipping one.

#### Scenario: Load older signals
- **WHEN** more signals exist than are shown and the user clicks Load older
- **THEN** the next 100 older signals are added below the list

#### Scenario: Signals sharing a time
- **WHEN** several triggers fired on one bar and those signals fall on either side of a page boundary
- **THEN** each appears exactly once

#### Scenario: All signals shown
- **WHEN** every matching signal is listed
- **THEN** the view no longer offers to load more

### Requirement: Signal History filter
The Signal History view SHALL let the user show all signals or only those from one trigger: relative volume, EMA cross, VWAP cross, VWAP band above, VWAP band below, RSI above, or RSI below.

#### Scenario: Filter by trigger
- **WHEN** the user selects EMA cross
- **THEN** only EMA cross signals are listed, and Load older continues within that filter

### Requirement: Signal History stays current
While the Signal History view is open, new signals matching the filter SHALL appear at the top within 15 seconds, without losing older signals already loaded.

#### Scenario: Signal fires while open
- **WHEN** a signal is recorded while the view is open and has older signals loaded
- **THEN** it appears at the top within 15 seconds and the older signals stay listed

### Requirement: Live settings
Signal settings SHALL be editable in the Signals view, persisted locally, validated, and applied without restarting. Changing the timeframe or an indicator period SHALL rebuild the indicators from history.

#### Scenario: Invalid settings
- **WHEN** the user sets the fast EMA longer than the slow EMA
- **THEN** the save is rejected with an explanation

#### Scenario: RSI levels out of order
- **WHEN** the user sets the RSI lower level at or above the upper level
- **THEN** the save is rejected with an explanation

### Requirement: Replay
The system SHALL provide a command that runs historical bars from a CSV file or a past IBKR session through the same rules and prints the signals instead of notifying, optionally running the LLM filter.

#### Scenario: Replaying a session
- **WHEN** the user replays a past date
- **THEN** the signals that the live rules would have raised that day are listed
