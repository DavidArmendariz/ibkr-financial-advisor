# money-supply Specification

## Purpose

Shows the US M2 money supply from FRED, as its level and its year-over-year growth, with an explanation of what M2 is and how to read it. It gives liquidity context only: it raises no alerts and places no orders.

## Requirements

### Requirement: M2 Money Supply view in the sidebar
The sidebar SHALL list an M2 Money Supply item, directly below Fundamentals, that opens the M2 Money Supply view.

#### Scenario: Open the view
- **WHEN** the user clicks M2 Money Supply in the sidebar
- **THEN** the view opens and the item is shown as selected

### Requirement: M2 data source
The system SHALL use FRED series M2SL: the monthly, seasonally adjusted US M2 money stock, in billions of dollars, from January 1959 onward. It SHALL use the FRED key saved for the Calendar and SHALL NOT need an IBKR connection.

#### Scenario: Disconnected from IBKR
- **WHEN** the app isn't connected to TWS and a FRED key is saved
- **THEN** the view still shows M2 data

### Requirement: Latest reading
The view SHALL show the latest M2 value, the month it covers, the change from the previous month and from the same month a year earlier (each in dollars and percent), when FRED last updated the series, and the next scheduled release date when FRED publishes one.

#### Scenario: Latest month shown
- **WHEN** the newest observation is for September 2026
- **THEN** the view labels the value as September 2026, with its month-over-month and year-over-year changes

#### Scenario: Next release unknown
- **WHEN** FRED doesn't list an upcoming release date
- **THEN** the next-release field is left out and the rest still shows

### Requirement: Year-over-year growth
For each month that has an observation 12 months earlier, the system SHALL compute year-over-year growth as the percent change from that observation. Months without one SHALL have no growth value.

#### Scenario: First year of data
- **WHEN** the month is in 1959
- **THEN** it has a level but no growth value

#### Scenario: Contraction
- **WHEN** M2 is lower than it was 12 months earlier
- **THEN** that month's growth is negative

### Requirement: M2 charts
The view SHALL show a chart of the M2 level and a chart of year-over-year growth over the same months. The growth chart SHALL mark zero and show negative growth in a different color from positive growth. Hovering a month in either chart SHALL show its date, level and growth.

#### Scenario: Hover a month
- **WHEN** the user hovers March 2021 in either chart
- **THEN** a tooltip shows March 2021 with its M2 level and year-over-year growth

### Requirement: Chart range
The view SHALL let the user choose the range of both charts: 5 years, 10 years, 25 years, or all data. The default is 10 years, and the view SHALL remember the choice across visits.

#### Scenario: Change range
- **WHEN** the user picks 25 years
- **THEN** both charts show the last 25 years of observations

### Requirement: M2 explanation
The view SHALL include an explanation of what M2 is and what it includes, how it differs from M1, why its growth matters for inflation, liquidity and asset prices, how to read the level and growth charts, and its limits as a market signal.

#### Scenario: Read the explanation
- **WHEN** the user opens the view
- **THEN** the explanation is on the page, and it says that M2 gives context rather than timing signals

### Requirement: FRED key needed
When no FRED key is saved, the view SHALL say that M2 data needs a FRED key and SHALL link to Settings, where the key is entered. The explanation SHALL still show.

#### Scenario: No key
- **WHEN** the user opens the view without a saved FRED key
- **THEN** the view says a FRED key is needed, links to Settings, and still shows the explanation

#### Scenario: Key added
- **WHEN** the user saves a FRED key in Settings and returns to the view
- **THEN** the view loads M2 data without a restart

### Requirement: M2 refresh and caching
The system SHALL refresh M2 data at least every 6 hours and save it locally. When a refresh fails, the system SHALL keep showing the saved data, say when it was last updated and why the refresh failed, and retry within an hour.

#### Scenario: FRED unreachable
- **WHEN** FRED can't be reached and data was saved earlier
- **THEN** the view shows the saved data with the error and the last update time

#### Scenario: After restart offline
- **WHEN** the app restarts without internet
- **THEN** the saved M2 data still shows

### Requirement: Key stays in the backend
The renderer SHALL NOT receive the FRED key, and error messages shown in the view SHALL NOT include it.

#### Scenario: Error message
- **WHEN** a FRED request fails
- **THEN** the view shows the failure's type or HTTP status, but not the request URL or the key
