# Spec Delta

## MODIFIED Requirements

### Requirement: Read-only brokerage access
The system's main IBKR connection SHALL be read-only. Orders SHALL be placed, modified, or cancelled only by the order entry feature, through a separate trading session on its own client ID, and only after the user confirms. Reading existing orders is permitted on the main connection.

#### Scenario: Connection is read-only
- **WHEN** the app connects to TWS or IB Gateway
- **THEN** its main connection requests a read-only API session, and no feature other than order entry issues a request that places, modifies, or cancels an order

#### Scenario: Reading open orders
- **WHEN** the open orders view requests the account's open orders
- **THEN** the request only reads orders and leaves them unchanged

#### Scenario: Trading session
- **WHEN** the user confirms an order review
- **THEN** the order goes through the trading session, connected to the same TWS and account as the main connection
