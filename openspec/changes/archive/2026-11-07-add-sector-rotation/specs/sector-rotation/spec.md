# Spec Delta

## Purpose

Shows how sector ETFs move relative to the S&P 500 on a Relative Rotation Graph, so the user can see where money is rotating. Context only: it raises no alerts and places no orders.

## ADDED Requirements

### Requirement: Sector Rotation view in the sidebar
The sidebar SHALL list a Sector Rotation item, directly below Asia & Europe, that opens the Sector Rotation view.

#### Scenario: Open the view
- **WHEN** the user clicks Sector Rotation in the sidebar
- **THEN** the view opens and the item is shown as selected

### Requirement: Rotation readings
For each of XLK, XLC, XLY, XLF, XLI, XLB, XLE, XLV, XLP, XLU, XLRE, and SMH, the system SHALL compute relative strength against SPY as the ratio of their closes. It SHALL derive an RS-Ratio from how far that strength is above or below its recent average, and an RS-Momentum from how fast the RS-Ratio is changing. Both are centred on 100 over a 10-period lookback, using completed sessions only.

#### Scenario: Outperforming and accelerating
- **WHEN** an ETF's strength against SPY is above its recent average and rising faster than usual
- **THEN** both its readings are above 100

#### Scenario: Session in progress
- **WHEN** the market is open
- **THEN** today's partial bar is left out

### Requirement: Quadrants
Each ETF SHALL be placed in Leading (both readings at or above 100), Weakening (RS-Ratio at or above 100, momentum below), Lagging (both below 100), or Improving (RS-Ratio below 100, momentum at or above).

#### Scenario: Fading leader
- **WHEN** an ETF's RS-Ratio is 102 and its momentum is 99
- **THEN** it is in Weakening

### Requirement: Rotation graph
The view SHALL plot each ETF as a trail of its last readings, 8 by default and adjustable from 3 to 20, ending at a labelled current point. The graph SHALL have RS-Ratio on the horizontal axis and RS-Momentum on the vertical axis, with the four quadrants marked around 100. SMH SHALL stand out, and other ETFs SHALL highlight on hover or selection.

#### Scenario: Direction of travel
- **WHEN** the user looks at an ETF's trail
- **THEN** it ends at the current reading, so the direction it's moving shows

#### Scenario: Hover
- **WHEN** the user hovers a point
- **THEN** a tooltip shows the ETF, the date, both readings, and the quadrant

### Requirement: Weekly and daily
The view SHALL default to weekly readings, built from daily bars with weeks ending on Friday, and SHALL offer daily readings. The choice and trail length SHALL be remembered between launches.

#### Scenario: Switch to daily
- **WHEN** the user selects daily
- **THEN** the graph and table show daily readings

### Requirement: Rotation table
Below the graph, a table SHALL list each ETF with its sector name, quadrant, RS-Ratio, RS-Momentum, and how many periods it has been in its current quadrant, so the readings are available without the graph.

#### Scenario: Sorted by quadrant
- **WHEN** the table shows
- **THEN** rows are grouped Leading, Weakening, Lagging, Improving

### Requirement: Data refresh and errors
The system SHALL fetch two years of daily bars for SPY and each ETF at most once per session, and SHALL keep the last readings if a refresh fails. An ETF whose bars IBKR refuses SHALL show the error and be left off the graph, without affecting the others. If SPY can't be fetched, the view SHALL say so.

#### Scenario: One ETF refused
- **WHEN** IBKR refuses data for XLRE
- **THEN** XLRE shows the error in the table, and the other ETFs plot normally

#### Scenario: Not connected
- **WHEN** IBKR is disconnected
- **THEN** the view keeps the last readings, marked as stale

### Requirement: Context only
The Sector Rotation view SHALL NOT raise alerts, change signals, or place, modify, or cancel orders. It SHALL say that RS-Ratio and RS-Momentum are the app's own approximation of the RRG method, not the official values.

#### Scenario: Reading the view
- **WHEN** the user opens the view
- **THEN** a note says the readings are an approximation
