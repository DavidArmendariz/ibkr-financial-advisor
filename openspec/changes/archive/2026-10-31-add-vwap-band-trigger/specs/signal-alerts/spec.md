# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Indicators
On each completed bar the system SHALL compute session VWAP (from 09:30 ET, or 04:00 ET when pre-market is included) and the volume-weighted standard deviation of typical price around it, a fast and slow EMA (default 9 and 21), Bollinger Bands (default 20 periods, 2 standard deviations), and relative volume against the average of the previous bars (default 20).

#### Scenario: VWAP resets each session
- **WHEN** a new trading session starts
- **THEN** VWAP and its standard deviation restart from that session's first bar

### Requirement: Trigger switches
The Signals settings SHALL group triggers into Volume and Technical categories, each trigger with an on/off switch. By default relative volume, EMA cross, and VWAP band are on and VWAP cross is off.

#### Scenario: First use
- **WHEN** the user has never changed the trigger switches
- **THEN** the Signals settings show relative volume, EMA cross, and VWAP band on and VWAP cross off, under their categories

#### Scenario: Switch applied live
- **WHEN** the user turns a trigger on or off and saves
- **THEN** the next completed bar uses the new switches, without a restart or a rebuild of the indicators

#### Scenario: Switches survive a restart
- **WHEN** the user changes a trigger switch and restarts the app
- **THEN** the switch keeps its saved state

#### Scenario: All triggers off
- **WHEN** the user turns every trigger off and saves
- **THEN** the save succeeds and no signals are raised

### Requirement: Signal History filter
The Signal History view SHALL let the user show all signals or only those from one trigger: relative volume, EMA cross, VWAP cross, VWAP band above, or VWAP band below.

#### Scenario: Filter by trigger
- **WHEN** the user selects EMA cross
- **THEN** only EMA cross signals are listed, and Load older continues within that filter
