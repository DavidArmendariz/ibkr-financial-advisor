# signal-analysis Specification

## Purpose

Lets the user study recorded signals on demand with the configured AI provider: a pre-mortem limited to what was known when the signal fired, and a post-mortem that judges it with hindsight. Analysis only; no orders are placed.

## Requirements

### Requirement: On-demand analysis
Each signal in the Signal History view SHALL offer Pre-mortem and Post-mortem actions. An analysis SHALL run only when the user requests it, and SHALL NOT affect notifications, the LLM filter, or the signal's saved record.

#### Scenario: Request an analysis
- **WHEN** the user clicks Pre-mortem on a signal
- **THEN** the view shows that it's running, then shows the result under that signal

#### Scenario: Other signals stay usable
- **WHEN** an analysis is running
- **THEN** the user can keep browsing and filtering Signal History

### Requirement: Pre-mortem uses only what was known then
The pre-mortem SHALL use only the signal's saved snapshot and session bars that closed at or before the signal's time. It SHALL NOT receive any later data, and SHALL return take or skip, a confidence, the case for the signal, the risks, and what would prove it wrong.

#### Scenario: Bars after the signal exist
- **WHEN** a pre-mortem runs after the session has ended
- **THEN** no bar closing after the signal's time is sent to the provider

#### Scenario: Run days later
- **WHEN** the same signal is analyzed on two different days
- **THEN** the data sent is the same both times

### Requirement: Post-mortem measures what happened
The post-mortem SHALL use the signal's data plus the bars from later that session, with outcome figures computed by the system: return after 15, 30, and 60 minutes and at the close, the largest gain and loss before the close, and whether price passed its starting level again.

#### Scenario: Provider never computes outcomes
- **WHEN** a post-mortem runs
- **THEN** the system computes the outcome figures, and the provider receives them as given values

#### Scenario: Signal is too recent
- **WHEN** the user requests a post-mortem less than 15 minutes after the signal, or fewer than 15 minutes remained in the session
- **THEN** the request is refused with an explanation, and no provider call is made

#### Scenario: Signal late in the session
- **WHEN** a horizon falls after the session's close
- **THEN** that figure shows as not available

### Requirement: Post-mortem verdict
The post-mortem SHALL return a verdict of good, bad, or mixed, with an explanation, and SHALL state that it was written with hindsight. The upward EMA cross, VWAP cross, and VWAP band above signals SHALL be judged as long entries. Relative volume, VWAP band below, RSI above, and RSI below signals SHALL be judged in both directions, because they don't imply one.

#### Scenario: Upward signal
- **WHEN** a post-mortem runs on an EMA cross signal
- **THEN** the verdict judges a long entry at the signal's price

#### Scenario: Signal without a direction
- **WHEN** a post-mortem runs on a relative volume signal
- **THEN** the result covers how a long and a short entry would each have done

### Requirement: Saved analyses
The system SHALL save the latest pre-mortem and post-mortem for each signal, with the time, provider, and model, and show them in Signal History after a restart. Running one again SHALL replace the saved one only if the new run succeeds.

#### Scenario: After restart
- **WHEN** the app restarts
- **THEN** saved analyses still show under their signals

#### Scenario: Failed rerun
- **WHEN** a rerun fails
- **THEN** the previous analysis stays, and the error is shown

### Requirement: Analysis failures
When an analysis can't run, the system SHALL tell the user why and SHALL NOT save a result. This covers no configured provider, no IBKR connection, unavailable bars, a provider error, an invalid reply, and a timeout of 60 seconds.

#### Scenario: No provider configured
- **WHEN** the user requests an analysis with no AI provider configured
- **THEN** the view says so and points to Settings

#### Scenario: Bars unavailable
- **WHEN** IBKR can't supply the session's bars
- **THEN** the view shows the reason and no provider call is made

### Requirement: Analysis data boundaries
An analysis SHALL send only market data for the signal and outcome figures to the configured provider. It SHALL NOT send positions, orders, balances, or account identifiers, and SHALL NOT place, modify, or cancel orders.

#### Scenario: Analyzing a signal
- **WHEN** an analysis runs
- **THEN** no account data is requested or sent, and no order is placed
