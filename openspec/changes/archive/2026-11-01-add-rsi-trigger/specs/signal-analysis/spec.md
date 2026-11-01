# Spec Delta

## MODIFIED Requirements

### Requirement: Post-mortem verdict
The post-mortem SHALL return a verdict of good, bad, or mixed, with an explanation, and SHALL state that it was written with hindsight. The upward EMA cross, VWAP cross, and VWAP band above signals SHALL be judged as long entries. Relative volume, VWAP band below, RSI above, and RSI below signals SHALL be judged in both directions, because they don't imply one.

#### Scenario: Upward signal
- **WHEN** a post-mortem runs on an EMA cross signal
- **THEN** the verdict judges a long entry at the signal's price

#### Scenario: Signal without a direction
- **WHEN** a post-mortem runs on a relative volume signal
- **THEN** the result covers how a long and a short entry would each have done
