# macro-indicators Specification

## Purpose

Shows the macro market context that moves SOXL (crude oil, gold, S&P 500, Nasdaq 100 and Dow futures and indexes, the US 10-year Treasury yield and the VIX) live from IBKR, plus the official USD/COP rate, in a dedicated Macro view.

## Requirements

### Requirement: Macro view in the sidebar
The sidebar SHALL list a Macro item, between Gamma and Settings, that opens the Macro view.

#### Scenario: Open the Macro view
- **WHEN** the user clicks Macro in the sidebar
- **THEN** the Macro view opens and the Macro item is shown as selected

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

### Requirement: Indicators shown
The Macro view SHALL show these indicators: crude oil, gold, the US 10-year Treasury yield, the VIX, and USD/COP on one card each, and the S&P 500, Nasdaq 100 and Dow Jones futures and spot indexes on one combined card per index. The futures are the NYMEX WTI, COMEX gold, CME E-mini S&P 500, CME E-mini Nasdaq-100 and CBOT E-mini Dow front months. Values are in index points, except crude oil ($/bbl), gold ($/oz), the yield (%) and USD/COP (pesos per dollar).

#### Scenario: All cards
- **WHEN** the user opens the Macro view while connected with market data available
- **THEN** it shows S&P 500, Nasdaq 100, Dow Jones, 10Y yield, VIX, Crude oil, Gold and USD/COP cards, with each of the 11 indicators showing its last value or the reason it has none

### Requirement: Indicator sections
The Macro view SHALL group its cards under three labelled sections, in this order: Equity indexes (S&P 500, Nasdaq 100, Dow Jones), Rates & volatility (US 10-year yield, VIX), and Commodities & currency (crude oil, gold, USD/COP).

#### Scenario: Sections in order
- **WHEN** the user opens the Macro view
- **THEN** the three sections appear in order, each with its label and its cards in the listed order

#### Scenario: Narrow window
- **WHEN** the window is too narrow for a section's cards to fit side by side
- **THEN** that section's cards wrap to fewer columns in the same order, with no horizontal scrolling

### Requirement: Combined index cards
Each equity index SHALL have one card showing its futures first and its spot index below, each with its own value, unit, and change.

#### Scenario: Futures and spot together
- **WHEN** the S&P 500 card has data for both
- **THEN** it shows the S&P 500 futures value and change, naming the contract, and below them the SPX value and change

#### Scenario: One side has no value
- **WHEN** an index card has a value for only one of futures or spot
- **THEN** that value still shows, and the other side shows its error or that it has no value

### Requirement: Change since previous close
Each indicator SHALL show the change and percent change of the last value against the previous session's close. The 10-year yield's change SHALL be shown in basis points instead of a percent change.

#### Scenario: Price moves up
- **WHEN** crude oil last traded at 72.40 and the previous close was 71.90
- **THEN** the card shows +0.50 and +0.70%, styled as a gain

#### Scenario: Yield change
- **WHEN** the 10-year yield is 4.31% and the previous close was 4.25%
- **THEN** the card shows +6 bp

#### Scenario: Index card
- **WHEN** an index's futures and spot index moved by different amounts
- **THEN** its card shows each one's own change

### Requirement: Live updates
The system SHALL stream the IBKR indicators while connected to IBKR, and the open Macro view SHALL show new values within 5 seconds of IBKR reporting them.

#### Scenario: Value changes
- **WHEN** IBKR reports a new NQ price while the Macro view is open
- **THEN** the NQ card shows it within 5 seconds without a manual refresh

### Requirement: Intraday sparkline
Each IBKR indicator's card SHALL show a sparkline of the indicator over the most recent session, refreshed at least every 5 minutes while the market for it is open. A combined index card SHALL show the sparkline of its futures only.

#### Scenario: Weekend
- **WHEN** the user opens the Macro view on a weekend
- **THEN** each sparkline shows the last session before the weekend

#### Scenario: Index card outside regular hours
- **WHEN** futures are trading and the spot index is closed
- **THEN** the index card's sparkline shows the futures session

### Requirement: Front-month rollover
For futures the system SHALL use the front-month contract as IBKR's continuous future selects it, re-check it at least once a day, and show the contract month on the card.

#### Scenario: Contract rolls
- **WHEN** IBKR's front month for crude oil moves from the December to the January contract
- **THEN** within a day the card switches to the January contract and names it

### Requirement: Data freshness
Each IBKR indicator SHALL state whether its value is live, delayed, or the last close because the market is closed, and the time of the last update. In a combined index card, the futures and the spot index SHALL each state their own.

#### Scenario: No real-time subscription
- **WHEN** the account has no real-time subscription for the futures exchange
- **THEN** the card shows IBKR's delayed value labelled as delayed

#### Scenario: Market closed
- **WHEN** the market for an indicator is closed
- **THEN** the card shows the last value labelled as closed with the time it was last updated

#### Scenario: Futures open and spot closed
- **WHEN** futures are trading and the spot index is closed
- **THEN** the index card labels the futures with their own state and the spot index as closed with its last update

### Requirement: Errors and disconnection
When IBKR refuses data for an indicator, including historical data when it has no value, its card SHALL show the IBKR error, and the system SHALL retry it every 5 minutes. The exception is historical data refused because the account lacks permission for it: the system SHALL NOT request that indicator's historical data again until the IBKR connection is re-established. When IBKR is not connected, the view SHALL say so and keep the last values it showed, marked as stale.

#### Scenario: Data refused
- **WHEN** IBKR refuses market data for the 10-year yield
- **THEN** that card shows IBKR's error message while the other cards keep updating

#### Scenario: Error on one side of an index card
- **WHEN** IBKR refuses data for the Dow Jones index while Dow futures have data
- **THEN** the Dow Jones card keeps showing the futures, and shows the error next to the spot index

#### Scenario: Historical data not permitted
- **WHEN** IBKR answers a request for Dow Jones bars with "No market data permissions"
- **THEN** the Dow Jones card shows that error next to the spot index while it has no value, and no more Dow Jones bars are requested while the connection stays up

#### Scenario: Permission re-checked after reconnecting
- **WHEN** Dow Jones bars were refused for lack of permission and the IBKR connection is then re-established, on the same or the other account
- **THEN** the system requests Dow Jones bars again

#### Scenario: Connection drops
- **WHEN** the IBKR connection drops while the Macro view is open
- **THEN** until the connection lock screen takes over, the view says it is not connected and the cards keep their last values marked as stale

#### Scenario: Reconnected
- **WHEN** the connection comes back and the user returns to the Macro view
- **THEN** the cards show the values from before the drop until new ones arrive

### Requirement: Official USD/COP rate
IBKR does not quote the Colombian peso, so the system SHALL take USD/COP from Banco de la República's official representative market rate (TRM) on Colombia's open-data portal. The card SHALL show the rate in force today in Bogotá time, its change against the previous rate, a sparkline of the last 30 rates, an "official daily rate" label with the dates the rate is valid for, and the system SHALL check for a new rate at least every hour.

#### Scenario: Weekend rate
- **WHEN** the user opens the Macro view on a Sunday and the TRM published on Friday is valid from Saturday to Monday
- **THEN** the USD/COP card shows that rate, its change against Friday's rate, and that it is valid Saturday to Monday

#### Scenario: Independent of IBKR
- **WHEN** IBKR refuses market data or is disconnected
- **THEN** the USD/COP card still shows the official rate and is not marked as stale

#### Scenario: Source unreachable
- **WHEN** the open-data portal cannot be reached
- **THEN** the card keeps the last rate it had, shows the error, and the system tries again within 5 minutes

### Requirement: Read-only market data
The Macro feature SHALL only read market data and contract details from IBKR and the public TRM rate from Colombia's open-data portal. It SHALL NOT request account data, send any account or user data to the open-data portal, or place orders.

#### Scenario: Using the Macro view
- **WHEN** the user opens the Macro view and it updates
- **THEN** no orders are placed, no account data is requested for it, and the request to the open-data portal carries only the query for public TRM rates

### Requirement: Delay shown on delayed cards
A card marked Delayed SHALL show how many minutes behind its data is, measured from the end of its latest 5-minute bar. Live and closed cards SHALL NOT show a delay.

#### Scenario: Delayed futures
- **WHEN** S&P 500 futures are delayed and their latest bar ended 10 minutes ago
- **THEN** the card says about 10 minutes behind

#### Scenario: Live data
- **WHEN** a subscription makes a card Live
- **THEN** it shows no delay

#### Scenario: No bars yet
- **WHEN** a delayed card has no bars
- **THEN** it says Delayed without a figure
