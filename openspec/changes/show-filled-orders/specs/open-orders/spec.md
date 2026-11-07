# Spec Delta

## ADDED Requirements

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
