# Spec Delta

## ADDED Requirements

### Requirement: EMA cross down trigger
The EMA cross down trigger, in the technical category, SHALL fire on the bar where the fast EMA crosses below the slow EMA. A cross requires the fast EMA at or above the slow EMA on the previous bar of the same session. It SHALL alert separately from the upward EMA cross, with its own switch and cooldown.

#### Scenario: Bearish cross
- **WHEN** the fast EMA crosses below the slow EMA during regular hours outside the blackouts
- **THEN** an EMA cross down signal is raised, shown on the chart as a downward marker

#### Scenario: EMA already below
- **WHEN** the fast EMA stays below the slow EMA without crossing on that bar
- **THEN** no EMA cross down signal is raised

#### Scenario: Upward cross only
- **WHEN** the fast EMA crosses above the slow EMA
- **THEN** only an EMA cross signal is raised, not an EMA cross down signal

#### Scenario: New session
- **WHEN** the first bar of a session has the fast EMA below the slow EMA after yesterday ended above
- **THEN** no signal is raised, because a cross needs the previous bar of the same session

## MODIFIED Requirements

### Requirement: Trigger switches
The Signals settings SHALL group triggers into Volume and Technical categories, each trigger with an on/off switch. By default relative volume, EMA cross, VWAP band, and RSI are on, and VWAP cross and EMA cross down are off.

#### Scenario: First use
- **WHEN** the user has never changed the trigger switches
- **THEN** the Signals settings show relative volume, EMA cross, VWAP band, and RSI on, and VWAP cross and EMA cross down off, under their categories

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
The Signal History view SHALL let the user show all signals or only those from one trigger: relative volume, EMA cross, EMA cross down, VWAP cross, VWAP band above, VWAP band below, RSI above, or RSI below.

#### Scenario: Filter by trigger
- **WHEN** the user selects EMA cross
- **THEN** only EMA cross signals are listed, and Load older continues within that filter
