# Spec Delta

## ADDED Requirements

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
The Signal History view SHALL let the user show all signals or only those from one trigger: relative volume, EMA cross, or VWAP cross.

#### Scenario: Filter by trigger
- **WHEN** the user selects EMA cross
- **THEN** only EMA cross signals are listed, and Load older continues within that filter

### Requirement: Signal History stays current
While the Signal History view is open, new signals matching the filter SHALL appear at the top within 15 seconds, without losing older signals already loaded.

#### Scenario: Signal fires while open
- **WHEN** a signal is recorded while the view is open and has older signals loaded
- **THEN** it appears at the top within 15 seconds and the older signals stay listed
