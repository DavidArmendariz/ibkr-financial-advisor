# signal-outcomes Specification

## Purpose

Measures what SOXL did after each recorded signal and reports the results per trigger against a baseline, so the user can see which alerts deserve attention. Measurement only; no orders are placed.

## Requirements

### Requirement: Signal outcome measurement
For every recorded signal, the system SHALL compute the percent move from the signal's bar close to 5, 15, and 30 minutes later, and the largest move up and down within those 30 minutes. It SHALL do so without any AI provider, including for signals the LLM filter skipped.

#### Scenario: Window has passed
- **WHEN** 30 minutes have passed since a signal and IBKR is connected
- **THEN** its figures are saved within 10 minutes

#### Scenario: Skipped by the LLM filter
- **WHEN** the LLM filter skipped a signal
- **THEN** its figures are still measured

#### Scenario: After a restart
- **WHEN** the app restarts
- **THEN** saved figures are kept and aren't requested again

### Requirement: Outcomes stay in regular hours
Outcome figures SHALL use only bars that close by that session's regular close, using IBKR's actual trading hours. A horizon past the close SHALL be not available, and the largest moves SHALL cover the part of the window before the close.

#### Scenario: Signal late in the session
- **WHEN** a signal fires 20 minutes before the close
- **THEN** the 5 and 15 minute figures are saved, the 30 minute figure is not available, and the largest moves cover those 20 minutes

#### Scenario: Half-day
- **WHEN** a session closes early
- **THEN** the early close is the limit

### Requirement: Earlier signals are measured
Signals recorded before this feature existed SHALL be measured the same way, one trading day per pass, newest first. A signal whose bars IBKR no longer has SHALL be marked not available and not requested again.

#### Scenario: First run
- **WHEN** the app first runs with recorded signals
- **THEN** they are measured over the following passes, without blocking the signal stream

#### Scenario: Bars too old
- **WHEN** IBKR returns no bars for a past day
- **THEN** that day's signals show as not available and are left out of the results

#### Scenario: Not connected
- **WHEN** IBKR is disconnected
- **THEN** measuring pauses and resumes after reconnecting, with nothing marked not available

### Requirement: Results per trigger
Signal History SHALL show a table with one row per trigger that has measured signals. For each of the 5, 15, and 30 minute horizons, it SHALL show the sample size, average move, median move, and share of moves up. It SHALL also show the average largest move up and down.

#### Scenario: A horizon has fewer signals
- **WHEN** some of a trigger's signals have no 30 minute figure
- **THEN** the 30 minute sample size counts only those that do

#### Scenario: No measured signals
- **WHEN** nothing has been measured yet
- **THEN** the table says so, and the signal list still works

#### Scenario: Still measuring
- **WHEN** signals are waiting to be measured
- **THEN** the view shows how many

### Requirement: Baseline comparison
The table SHALL include a baseline row with the same figures computed from every regular-hours minute of the days that have measured signals, so a trigger can be compared with no signal at all.

#### Scenario: Comparing a trigger
- **WHEN** the table shows a trigger
- **THEN** the baseline row is shown with it

#### Scenario: A rising market
- **WHEN** SOXL rose on most measured days
- **THEN** the baseline shows that rise, so a trigger's upward average isn't mistaken for an edge

### Requirement: Small samples are marked
Any figure based on fewer than 30 signals SHALL be marked as too few to rely on. The view SHALL state that results describe past signals and don't predict future ones.

#### Scenario: Few signals
- **WHEN** a trigger has 12 measured signals at a horizon
- **THEN** its figures for that horizon show as a small sample

### Requirement: Outcomes on each signal
Each signal's details in Signal History SHALL show its saved figures, or that they are pending or not available.

#### Scenario: Recent signal
- **WHEN** a signal is less than 30 minutes old
- **THEN** its details show that the outcome is pending

### Requirement: Outcomes change nothing else
Outcome tracking SHALL NOT change triggers, notifications, the LLM filter, or a signal's saved record, SHALL NOT call an AI provider, and SHALL NOT place, modify, or cancel orders.

#### Scenario: Measuring a signal
- **WHEN** a signal is measured
- **THEN** only historical bars are read from IBKR, and nothing leaves the machine
