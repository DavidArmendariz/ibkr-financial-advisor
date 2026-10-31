# Spec Delta

## MODIFIED Requirements

### Requirement: Read-only brokerage access
The system SHALL connect to IBKR in read-only mode and SHALL NOT place, modify, or cancel orders. Reading existing orders is permitted.

#### Scenario: Connection is read-only
- **WHEN** the app connects to TWS or IB Gateway
- **THEN** it requests a read-only API session and no feature issues a request that places, modifies, or cancels an order

#### Scenario: Reading open orders
- **WHEN** the open orders view requests the account's open orders
- **THEN** the request only reads orders and leaves them unchanged
