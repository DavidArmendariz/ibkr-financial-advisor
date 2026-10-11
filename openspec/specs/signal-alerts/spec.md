# signal-alerts Specification

## Purpose

Watches SOXL in real time and alerts the user to long entry setups found by deterministic technical rules, optionally screened by the configured AI provider. Alerts only; no orders are placed.

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
On each completed bar the system SHALL compute session VWAP (from 09:30 ET, or 04:00 ET when pre-market is included), a fast and slow EMA (default 9 and 21), Bollinger Bands (default 20 periods, 2 standard deviations), and relative volume against the average of the previous bars (default 20).

#### Scenario: VWAP resets each session
- **WHEN** a new trading session starts
- **THEN** VWAP restarts from that session's first bar

### Requirement: Long entry rule
The system SHALL raise a LONG entry signal when the bar's close crosses above VWAP, the fast EMA is above the slow EMA, and relative volume exceeds the threshold (default 1.5×). A cross requires the previous close at or below VWAP within the same session.

#### Scenario: Weak cross
- **WHEN** the close crosses above VWAP but relative volume is below the threshold
- **THEN** no signal is raised

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
Each notified signal SHALL produce a native desktop notification titled with the symbol, signal type, and price, showing key indicator values and the LLM's reason. Notifications SHALL arrive while the app is running even if its window is closed. Clicking a notification SHALL open the Signals view.

#### Scenario: Window closed
- **WHEN** a signal fires while the app's window is closed but the app is still running
- **THEN** a desktop notification appears

### Requirement: Signal history
Every signal SHALL be recorded locally, including ones the LLM filter skipped, with its snapshot, LLM decision, and whether it was notified. The Signals view SHALL show the latest 50, and they SHALL survive restarts.

#### Scenario: After restart
- **WHEN** the app restarts
- **THEN** previously recorded signals still appear in the Signals view

### Requirement: Signals view
The Signals view SHALL show a live chart of the symbol's bars with VWAP, both EMAs, Bollinger Bands, volume, and a marker at each signal; the IBKR connection, market data, and LLM filter status (including the IBKR error when market data is refused); current indicator values; the recent signals; and the settings.

#### Scenario: Missing market data subscription
- **WHEN** IBKR refuses the real-time subscription
- **THEN** the market data status shows IBKR's error and the system retries every 5 minutes

#### Scenario: Forming bar
- **WHEN** streaming is active
- **THEN** the chart's latest candle updates every 5 seconds before the bar completes

### Requirement: Live settings
Signal settings SHALL be editable in the Signals view, persisted locally, validated, and applied without restarting. Changing the timeframe or an indicator period SHALL rebuild the indicators from history.

#### Scenario: Invalid settings
- **WHEN** the user sets the fast EMA longer than the slow EMA
- **THEN** the save is rejected with an explanation

### Requirement: Replay
The system SHALL provide a command that runs historical bars from a CSV file or a past IBKR session through the same rules and prints the signals instead of notifying, optionally running the LLM filter.

#### Scenario: Replaying a session
- **WHEN** the user replays a past date
- **THEN** the signals that the live rules would have raised that day are listed
