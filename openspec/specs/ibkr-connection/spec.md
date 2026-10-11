# ibkr-connection Specification

## Purpose

Connects the app to a locally running TWS or IB Gateway session, safely: read-only, paper by default, and recovering on its own from drops.

## Requirements

### Requirement: Read-only brokerage access
The system SHALL connect to IBKR in read-only mode and SHALL NOT place, modify, or cancel orders.

#### Scenario: Connection is read-only
- **WHEN** the app connects to TWS or IB Gateway
- **THEN** it requests a read-only API session and no feature issues order requests

### Requirement: Automatic connection targets paper only
The system SHALL automatically connect only to the paper trading port. Connecting to the live port MUST require an explicit user action.

#### Scenario: Launch with paper TWS running
- **WHEN** the app starts and TWS is logged into the paper account
- **THEN** the app connects without user interaction

#### Scenario: Only live TWS running
- **WHEN** the paper port does not answer and the live port does
- **THEN** the app stays on the connection screen until the user clicks the live option

#### Scenario: Waiting for TWS to start
- **WHEN** no TWS session is reachable
- **THEN** the connection screen keeps retrying the paper port every 10 seconds

### Requirement: Reconnect after an unexpected drop
After a successful connection, the system SHALL reconnect to the same account if the connection drops without the user disconnecting, retrying with increasing delays capped at 60 seconds.

#### Scenario: TWS daily restart
- **WHEN** an established connection drops and TWS comes back on the same port
- **THEN** the app reconnects without user action and features that stream data resubscribe

#### Scenario: User disconnects
- **WHEN** the user clicks Disconnect
- **THEN** the app does not reconnect until the user connects again

#### Scenario: User switches account while a retry is pending
- **WHEN** a reconnect to the previous account is pending and the user connects to another account
- **THEN** the pending retry does not drop or replace the user's new connection

### Requirement: Connection status is visible
The system SHALL show whether it is connected, and whether to the paper or live account, at all times.

#### Scenario: Connected to paper
- **WHEN** the app is connected to the paper port
- **THEN** the sidebar shows "Connected · Paper"
