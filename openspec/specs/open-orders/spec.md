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

### Requirement: Filled orders list
The Orders view SHALL list filled orders below the open orders, newest first, for the connected mode, whichever client placed them, with the fill time, instrument, side, quantity, average price, venue, commission, and realized P&L.

#### Scenario: Order fills
- **WHEN** an open order fills
- **THEN** it leaves the open list and appears in the filled list

#### Scenario: Several fills for one order
- **WHEN** an order fills in parts
- **THEN** it shows as one row with the total quantity, the volume-weighted average price, and the latest time

#### Scenario: Overnight order
- **WHEN** an order fills overnight
- **THEN** the row shows the overnight venue

#### Scenario: Commission not reported yet
- **WHEN** IBKR hasn't reported a commission or P&L
- **THEN** those fields are empty, not zero

#### Scenario: Read-Only API on
- **WHEN** TWS has Read-Only API on
- **THEN** filled orders still show

#### Scenario: No fills
- **WHEN** IBKR returns no fills
- **THEN** the section says so

#### Scenario: Fills can't be read
- **WHEN** IBKR doesn't answer in time
- **THEN** the section says so, and open orders are unaffected

### Requirement: Filled orders stay current
The system SHALL refresh filled orders every 15 seconds while the view is open and with the refresh control.

#### Scenario: View left open
- **WHEN** an order fills while the view is open
- **THEN** it appears within the next refresh

### Requirement: Fills are saved locally
The system SHALL save every fill it receives to the local database, once per IBKR execution ID, every minute while connected and whichever view is open, keeping live and paper apart. It SHALL NOT store account numbers.

#### Scenario: After IBKR's window
- **WHEN** a saved fill is no longer returned by IBKR
- **THEN** it still shows

#### Scenario: After a restart
- **WHEN** the app restarts
- **THEN** saved fills still show

#### Scenario: Seen twice
- **WHEN** IBKR returns the same fill again
- **THEN** it counts once

#### Scenario: Late commission
- **WHEN** a commission or P&L arrives after the fill was saved
- **THEN** the saved fill gets it, and a later blank reply doesn't clear it

#### Scenario: Orders view never opened
- **WHEN** an order fills while another view is open
- **THEN** it's saved

#### Scenario: Live and paper
- **WHEN** the app connects to paper
- **THEN** only paper fills show
