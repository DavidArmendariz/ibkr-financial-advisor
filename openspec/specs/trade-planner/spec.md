# trade-planner Specification

## Purpose

Plans long trades in SOXL or SOXS with ATR-based stop loss, take profit, and position size, so the user can enter them in TWS. It calculates only and never places orders.

## Requirements

### Requirement: Trade Planner in the sidebar
The sidebar SHALL list a Trade Planner item, directly below Signal History, that opens the Trade Planner view.

#### Scenario: Open the planner
- **WHEN** the user clicks Trade Planner in the sidebar
- **THEN** the view opens and the item is shown as selected

### Requirement: ATR for SOXL and SOXS
The planner SHALL show, for both SOXL and SOXS, the last price, the live bid and ask, intraday ATR on the Signals timeframe with the Signals ATR period, and daily ATR over 14 sessions, each with ATR as a percent of price and the time of its data.

#### Scenario: Both symbols
- **WHEN** the user opens the planner while connected
- **THEN** SOXL and SOXS each show their price, bid and ask, intraday ATR, and daily ATR

#### Scenario: Planner closed
- **WHEN** the planner hasn't been requested for 2 minutes
- **THEN** the bid and ask stop streaming, freeing their market data lines

#### Scenario: Data refused
- **WHEN** IBKR refuses SOXS data
- **THEN** the SOXS values show IBKR's error, and SOXL still works

### Requirement: Stop, target, and size
For the chosen symbol and ATR basis, the planner SHALL calculate a long trade: stop at entry minus the stop multiple times ATR, target at entry plus the target multiple times ATR, and shares as the risk amount divided by the distance to the stop, rounded down. The entry SHALL default to the ask, or the last price when there's no ask, and be editable.

#### Scenario: Default plan
- **WHEN** SOXL is at 80.00 with intraday ATR 0.40, multiples 1.5 and 3, and $1,000 at risk
- **THEN** the stop is 79.40, the target is 81.20, and the size is 1,666 shares

#### Scenario: Results shown
- **WHEN** a plan is calculated
- **THEN** it shows the stop and target prices and percents, shares, position value, dollars at risk, dollars to the target, and the reward-to-risk ratio

#### Scenario: Invalid inputs
- **WHEN** ATR is missing or an input is zero or negative
- **THEN** no plan is shown, and the planner says why

### Requirement: Risk from the account
The risk amount SHALL be either a fixed dollar amount or a percent of the connected account's net liquidation value, defaulting to 1%. The planner SHALL warn when the position value exceeds the account's available funds.

#### Scenario: Percent of account
- **WHEN** net liquidation is $100,000 and risk is 1%
- **THEN** $1,000 is at risk

#### Scenario: Too large for the account
- **WHEN** the position value is above available funds
- **THEN** the planner warns, and still shows the plan

### Requirement: Planner settings
The stop multiple (default 1.5), target multiple (default 3), ATR basis (default intraday), and risk setting SHALL persist locally with a `PLANNER_` prefix and apply without a restart.

#### Scenario: Remembered
- **WHEN** the user changes the stop multiple and reopens the app
- **THEN** the planner keeps the new multiple

### Requirement: Values for TWS
The planner SHALL show the side, symbol, shares, entry, stop, and target as a bracket order to enter in TWS, with a control that copies them as text.

#### Scenario: Copy
- **WHEN** the user clicks Copy
- **THEN** the plan's values are copied to the clipboard

### Requirement: Planner never places orders
The planner SHALL NOT place, modify, or cancel orders, or offer any control that does.

#### Scenario: Using a plan
- **WHEN** the user has a plan on screen
- **THEN** the only actions are editing inputs and copying values
