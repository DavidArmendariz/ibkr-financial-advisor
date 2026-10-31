# Spec Delta

## ADDED Requirements

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

### Requirement: Trigger switches
The Signals settings SHALL group triggers into Volume and Technical categories, each trigger with an on/off switch. By default relative volume and EMA cross are on and VWAP cross is off.

#### Scenario: First use
- **WHEN** the user has never changed the trigger switches
- **THEN** the Signals settings show relative volume and EMA cross on and VWAP cross off, under their categories

#### Scenario: Switch applied live
- **WHEN** the user turns a trigger on or off and saves
- **THEN** the next completed bar uses the new switches, without a restart or a rebuild of the indicators

#### Scenario: Switches survive a restart
- **WHEN** the user changes a trigger switch and restarts the app
- **THEN** the switch keeps its saved state

#### Scenario: All triggers off
- **WHEN** the user turns every trigger off and saves
- **THEN** the save succeeds and no signals are raised

## MODIFIED Requirements

### Requirement: Desktop notifications
Each notified signal SHALL produce a native desktop notification titled with the symbol, trigger, and price, showing the trigger's category, key indicator values, and the LLM's reason. Notifications SHALL arrive while the app is running even if its window is closed. Clicking a notification SHALL open the Signals view.

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

## REMOVED Requirements

### Requirement: Long entry rule
**Reason**: Replaced by independent triggers, so a signal no longer needs a VWAP cross, EMA trend, and high volume on the same bar.
**Migration**: Use the VWAP cross, EMA cross, and relative volume triggers, each with its own switch. The combined rule is no longer available.
