# Spec Delta

## MODIFIED Requirements

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
