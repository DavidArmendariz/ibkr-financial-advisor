# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Indicators shown
The Macro view SHALL show these indicators: crude oil, gold, the US 10-year Treasury yield, the VIX, and USD/COP on one card each, and the S&P 500, Nasdaq 100 and Dow Jones futures and spot indexes on one combined card per index. The futures are the NYMEX WTI, COMEX gold, CME E-mini S&P 500, CME E-mini Nasdaq-100 and CBOT E-mini Dow front months. Values are in index points, except crude oil ($/bbl), gold ($/oz), the yield (%) and USD/COP (pesos per dollar).

#### Scenario: All cards
- **WHEN** the user opens the Macro view while connected with market data available
- **THEN** it shows S&P 500, Nasdaq 100, Dow Jones, 10Y yield, VIX, Crude oil, Gold and USD/COP cards, with each of the 11 indicators showing its last value or the reason it has none

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

### Requirement: Intraday sparkline
Each IBKR indicator's card SHALL show a sparkline of the indicator over the most recent session, refreshed at least every 5 minutes while the market for it is open. A combined index card SHALL show the sparkline of its futures only.

#### Scenario: Weekend
- **WHEN** the user opens the Macro view on a weekend
- **THEN** each sparkline shows the last session before the weekend

#### Scenario: Index card outside regular hours
- **WHEN** futures are trading and the spot index is closed
- **THEN** the index card's sparkline shows the futures session

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
