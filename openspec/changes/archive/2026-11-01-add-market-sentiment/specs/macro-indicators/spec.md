# Spec Delta

## ADDED Requirements

### Requirement: Market Sentiment card
The Macro view SHALL show a Market Sentiment card above its sections, with a score from 0 to 100, its band, each component's score, the last 60 days of the score, and the date of the data. The card SHALL state that the score is the app's own estimate and not CNN's Fear & Greed Index.

#### Scenario: Score available
- **WHEN** the user opens the Macro view and the score has been computed
- **THEN** the card shows the score, band, components, recent history, data date, and the statement that it isn't CNN's index

### Requirement: Sentiment explanation
The Market Sentiment card SHALL offer an explanation, closed by default, of how the score is calculated, what the bands mean, and for each component what it measures and how to read a high or low value, including why breadth is context only.

#### Scenario: Open the explanation
- **WHEN** the user clicks How it's calculated
- **THEN** the card shows the method, the bands, and each component's calculation and meaning

#### Scenario: Close the explanation
- **WHEN** the explanation is open and the user clicks it again
- **THEN** it closes and the card returns to its normal size

### Requirement: Sentiment bands
The score SHALL map to a band: 0–24 Extreme Fear, 25–44 Fear, 45–55 Neutral, 56–75 Greed, and 76–100 Extreme Greed, using the score rounded to a whole number.

#### Scenario: Band edge
- **WHEN** the score is 24.4
- **THEN** the card shows 24 and Extreme Fear

### Requirement: Sentiment components
The score SHALL combine four components from daily closes: S&P 500 against its 125-day average, VIX against its 50-day average with the direction inverted, the 20-day return of SPY minus TLT, and HYG/LQD against its 50-day average. RSP/SPY against its 50-day average SHALL be shown as a breadth reading marked as context only, and SHALL NOT affect the score.

#### Scenario: Breadth is context only
- **WHEN** the breadth reading changes
- **THEN** the card shows the new reading, and the score and its history don't change

#### Scenario: High volatility reads as fear
- **WHEN** VIX is far above its 50-day average
- **THEN** the volatility component scores low

### Requirement: Sentiment scoring
Each component SHALL score from 0 to 100 as the percentage of the last 252 trading days, including the latest, on which its value was at or below the latest value. The score SHALL be the equal-weighted average of the available scored components.

#### Scenario: Highest reading of the year
- **WHEN** a component's latest value is its highest of the last 252 trading days
- **THEN** that component scores 100

### Requirement: Partial sentiment data
When a component is unavailable, the card SHALL say which one and why, and the score SHALL use the remaining scored components, as long as at least three remain. With fewer than three, the card SHALL show that no score is available and the reasons.

#### Scenario: One component refused
- **WHEN** IBKR refuses data for HYG
- **THEN** the junk bond component shows the error and the score uses the other three

#### Scenario: Too few components
- **WHEN** only two scored components have data
- **THEN** the card shows no score and lists why

### Requirement: Sentiment refresh
The system SHALL compute the score after connecting to IBKR and refresh it at least hourly while connected. When IBKR is not connected, the card SHALL keep its last score, marked as stale.

#### Scenario: After the close
- **WHEN** a new daily close is available
- **THEN** the score and data date update within an hour

#### Scenario: Connection drops
- **WHEN** the IBKR connection drops while the Macro view is open
- **THEN** until the lock screen takes over, the card keeps its last score marked as stale
