# portfolio-dashboard Specification

## Purpose

Shows the connected account's balances, open positions, and price charts from live IBKR data.

## Requirements

### Requirement: Account summary
The system SHALL display net liquidation value, unrealized P&L, realized P&L, buying power, and cash for the connected account, refreshed periodically.

#### Scenario: Dashboard open
- **WHEN** the user opens the Dashboard while connected
- **THEN** the account summary cards show the current values and refresh every 15 seconds

### Requirement: Positions table
The system SHALL list open positions with symbol, asset class, quantity, average cost, market price, and P&L.

#### Scenario: No positions
- **WHEN** the account holds no positions
- **THEN** the table shows "No open positions"

### Requirement: Price chart for a position
The system SHALL chart a selected position's price history from IBKR with 1D, 5D, 1M, 3M, and 1Y periods.

#### Scenario: Selecting a position
- **WHEN** the user clicks a row in the positions table
- **THEN** a candlestick chart of that symbol loads for the selected period

#### Scenario: Daily bars
- **WHEN** the user selects 1M, 3M, or 1Y
- **THEN** the chart loads daily bars without error
