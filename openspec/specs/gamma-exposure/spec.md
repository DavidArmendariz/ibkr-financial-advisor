# gamma-exposure Specification

## Purpose

Estimates dealer gamma exposure in SOXL options to show where hedging flows may concentrate: net exposure, the zero-gamma level, and the call and put walls.

## Requirements

### Requirement: Per-option exposure
For options within the configured expiration window (default 45 days) and strike range (default ±25% of the current price), the system SHALL compute each option's dollar gamma per 1% move in the underlying as gamma × open interest × contract multiplier × price² × 1%, counting calls as positive and puts as negative.

#### Scenario: Put exposure is negative
- **WHEN** a put has open interest and positive gamma
- **THEN** its exposure counts as negative

### Requirement: Exposure summary
The system SHALL report net, call, and put exposure; exposure by strike and by expiration; the call wall (strike with the largest call exposure); and the put wall (strike with the largest put exposure).

#### Scenario: Net exposure sign
- **WHEN** put exposure outweighs call exposure
- **THEN** net exposure is negative and the view labels it as a negative-gamma regime

### Requirement: Zero-gamma level
The system SHALL find the price, within ±30% of the current price and nearest to it, at which net exposure changes sign, by re-pricing every option's gamma from its own implied volatility at hypothetical prices. It SHALL report none when exposure does not change sign in that range.

#### Scenario: One-sided positioning
- **WHEN** all exposure in range is from calls
- **THEN** the zero-gamma level is reported as none in range

### Requirement: Open interest outside market hours
The system SHALL save the most recent open interest for each contract and use it when IBKR does not report open interest. The view SHALL show how many contracts have open interest and SHALL warn when more than 20% are missing.

#### Scenario: Weekend view
- **WHEN** the user opens the Gamma view on a weekend after a refresh during the previous session
- **THEN** exposure is computed from the saved open interest and the view states when it was saved

#### Scenario: No saved open interest
- **WHEN** most contracts have no open interest
- **THEN** the view shows a warning that the figures are incomplete

### Requirement: Refresh
The system SHALL refresh once after connecting, then on the configured interval (default 15 minutes) during market hours, and on demand from a Refresh control that shows progress. The latest result SHALL survive restarts.

#### Scenario: Manual refresh
- **WHEN** the user clicks Refresh
- **THEN** the control shows how many contracts have been fetched until the calculation completes

### Requirement: Disclosure of assumptions
The view SHALL state that exposure assumes dealers are long calls and short puts and is an estimate, not a forecast.

#### Scenario: Opening the view
- **WHEN** the user opens the Gamma view
- **THEN** the assumption is stated in the header
