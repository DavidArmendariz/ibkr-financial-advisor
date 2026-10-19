# macro-indicators Specification

## Purpose

Shows the macro market context that moves SOXL (crude oil, gold, S&P 500, Nasdaq 100 and Dow futures and indexes, the US 10-year Treasury yield and the VIX) live from IBKR, plus the official USD/COP rate, in a dedicated Macro view.

## Requirements

### Requirement: Macro view in the sidebar
The sidebar SHALL list a Macro item, between Gamma and Settings, that opens the Macro view.

#### Scenario: Open the Macro view
- **WHEN** the user clicks Macro in the sidebar
- **THEN** the Macro view opens and the Macro item is shown as selected

### Requirement: Indicators shown
The Macro view SHALL show one card each, in this order, for: crude oil, gold, S&P 500 futures, Nasdaq 100 futures, Dow futures, the US 10-year Treasury yield, the VIX, USD/COP, and the S&P 500, Nasdaq 100 and Dow Jones Industrial Average spot indexes. The futures are the NYMEX WTI, COMEX gold, CME E-mini S&P 500, CME E-mini Nasdaq-100 and CBOT E-mini Dow front months. Values are in index points, except crude oil ($/bbl), gold ($/oz), the yield (%) and USD/COP (pesos per dollar).

#### Scenario: All cards
- **WHEN** the user opens the Macro view while connected with market data available
- **THEN** it shows Crude oil, Gold, S&P 500 futures, NQ, Dow futures, 10Y yield, VIX, USD/COP, S&P 500, Nasdaq 100 and Dow Jones cards, each with its last value or the reason it has none

### Requirement: Change since previous close
Each card SHALL show the change and percent change of the last value against the previous session's close. The 10-year yield's change SHALL be shown in basis points instead of a percent change.

#### Scenario: Price moves up
- **WHEN** crude oil last traded at 72.40 and the previous close was 71.90
- **THEN** the card shows +0.50 and +0.70%, styled as a gain

#### Scenario: Yield change
- **WHEN** the 10-year yield is 4.31% and the previous close was 4.25%
- **THEN** the card shows +6 bp

### Requirement: Live updates
The system SHALL stream the IBKR indicators while connected to IBKR, and the open Macro view SHALL show new values within 5 seconds of IBKR reporting them.

#### Scenario: Value changes
- **WHEN** IBKR reports a new NQ price while the Macro view is open
- **THEN** the NQ card shows it within 5 seconds without a manual refresh

### Requirement: Intraday sparkline
Each IBKR indicator's card SHALL show a sparkline of the indicator over the most recent session, refreshed at least every 5 minutes while the market for it is open.

#### Scenario: Weekend
- **WHEN** the user opens the Macro view on a weekend
- **THEN** each sparkline shows the last session before the weekend

### Requirement: Front-month rollover
For futures the system SHALL use the front-month contract as IBKR's continuous future selects it, re-check it at least once a day, and show the contract month on the card.

#### Scenario: Contract rolls
- **WHEN** IBKR's front month for crude oil moves from the December to the January contract
- **THEN** within a day the card switches to the January contract and names it

### Requirement: Data freshness
Each IBKR indicator's card SHALL state whether its value is live, delayed, or the last close because the market is closed, and the time of the last update.

#### Scenario: No real-time subscription
- **WHEN** the account has no real-time subscription for the futures exchange
- **THEN** the card shows IBKR's delayed value labelled as delayed

#### Scenario: Market closed
- **WHEN** the market for an indicator is closed
- **THEN** the card shows the last value labelled as closed with the time it was last updated

### Requirement: Errors and disconnection
When IBKR refuses data for an indicator, including historical data when the card has no value, its card SHALL show the IBKR error, and the system SHALL retry it every 5 minutes. The exception is historical data refused because the account lacks permission for it: the system SHALL NOT request that indicator's historical data again until the IBKR connection is re-established. When IBKR is not connected, the view SHALL say so and keep the last values it showed, marked as stale.

#### Scenario: Data refused
- **WHEN** IBKR refuses market data for the 10-year yield
- **THEN** that card shows IBKR's error message while the other cards keep updating

#### Scenario: Historical data not permitted
- **WHEN** IBKR answers a request for Dow Jones bars with "No market data permissions"
- **THEN** the Dow Jones card shows that error while it has no value, and no more Dow Jones bars are requested while the connection stays up

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
