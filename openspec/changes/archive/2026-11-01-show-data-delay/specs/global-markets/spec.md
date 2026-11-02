# Spec Delta

## ADDED Requirements

### Requirement: KOSPI 200 estimate
While the Korean market is open and KODEX 200 ETF data is newer than the index's, the KOSPI 200 card SHALL show an estimated current value: the index's previous close moved by the ETF's percent change. It SHALL be labelled as an estimate from the ETF, and the real index value SHALL stay on the card.

#### Scenario: Index lags the stocks
- **WHEN** the index's latest bar is 20 minutes older than the ETF's
- **THEN** the card shows the estimate with its percent change, and the real index value

#### Scenario: Market closed
- **WHEN** Korea is closed
- **THEN** no estimate shows, because the real close is available

#### Scenario: ETF unavailable
- **WHEN** ETF data is missing
- **THEN** the card shows only the real index value

### Requirement: Delay shown
Each open instrument's card or table row SHALL show how many minutes behind its newest data is, measured from the end of its latest bar. Data under 2 minutes old SHALL show as current. A closed market SHALL show no delay.

#### Scenario: Delayed index
- **WHEN** the Nikkei 225's latest bar ended 17 minutes ago
- **THEN** its card says about 17 minutes behind

#### Scenario: Forming bar
- **WHEN** the latest bar hasn't ended yet
- **THEN** the data shows as current

#### Scenario: Closed market
- **WHEN** Amsterdam is closed
- **THEN** ASML's row shows no delay
