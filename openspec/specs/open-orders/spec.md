# open-orders Specification

## Purpose

Shows the connected account's current open orders in their own view, so working orders can be checked without switching to TWS. The view only reads orders and offers no way to change them.

## Requirements

### Requirement: Orders view in the sidebar
The system SHALL provide an Orders item in the sidebar, directly below Dashboard, that opens the open orders view.

#### Scenario: Open the view
- **WHEN** the user clicks Orders in the sidebar
- **THEN** the open orders view is shown and the Orders item is marked as selected

### Requirement: Open orders list
The system SHALL list every open order on the connected account, whichever client placed it, with instrument, side, order type, total, filled and remaining quantity, limit price, stop price, time in force, and status.

#### Scenario: Order placed in TWS
- **WHEN** the account has a working order that was placed manually in TWS
- **THEN** the order appears in the list

#### Scenario: Option order
- **WHEN** an open order is for an option
- **THEN** its instrument shows the symbol, expiry, strike, and right

#### Scenario: Price does not apply
- **WHEN** an order has no limit or stop price, such as a market order
- **THEN** that field shows as empty rather than as a number

#### Scenario: Order no longer working
- **WHEN** an order has been filled or cancelled
- **THEN** it is not listed

#### Scenario: No open orders
- **WHEN** the account has no open orders
- **THEN** the view shows "No open orders"

### Requirement: Open orders stay current
The system SHALL refresh the list every 15 seconds while the view is open and on demand from a refresh control, and SHALL NOT request open orders while the view is closed.

#### Scenario: View left open
- **WHEN** an order fills while the view is open
- **THEN** it leaves the list within the next refresh

#### Scenario: Manual refresh
- **WHEN** the user clicks the refresh control
- **THEN** the list is requested again immediately

#### Scenario: View closed
- **WHEN** the user switches to another view
- **THEN** the system stops requesting open orders until the view is opened again

### Requirement: Orders view is read-only
The system SHALL NOT offer any control in the orders view that places, modifies, or cancels an order.

#### Scenario: Viewing an order
- **WHEN** the user views or clicks an order in the list
- **THEN** no order action is available

### Requirement: Unreadable orders are reported
The system SHALL tell the user when open orders could not be read, and SHALL NOT present that as an empty list.

#### Scenario: TWS refuses or does not answer
- **WHEN** TWS rejects the request or does not answer in time
- **THEN** the view explains that orders could not be read, mentions that the Read-Only API setting can cause this, and states that turning it off removes TWS's own block on order placement

#### Scenario: No repeated requests after a refusal
- **WHEN** orders could not be read
- **THEN** automatic refresh stops, so TWS does not raise repeated pop-ups, and the list is requested again only when the user clicks refresh or reopens the view

#### Scenario: Not connected
- **WHEN** the connection to IBKR is lost while the view is open
- **THEN** the view says it is not connected, and the list refreshes on its own after reconnecting
