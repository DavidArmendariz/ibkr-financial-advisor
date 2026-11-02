# global-markets Specification

## Purpose

Shows Asian and European indexes and chip stocks from IBKR in one view, so the user can see how those markets moved before and during the US session. Read-only market data; no orders are placed.

## Requirements

### Requirement: Asia & Europe view in the sidebar
The sidebar SHALL list an Asia & Europe item, directly below Macro, that opens the Asia & Europe view.

#### Scenario: Open the view
- **WHEN** the user clicks Asia & Europe in the sidebar
- **THEN** the view opens and the item is shown as selected

### Requirement: Instruments shown
The view SHALL show, in this order, an Indexes section (Nikkei 225, KOSPI 200, KODEX 200 ETF, AEX, Euro Stoxx 50) as cards, and a Chip stocks section as one table in this market order: Korea (Samsung Electronics, SK Hynix), Taiwan (TSMC), Japan (Tokyo Electron, Advantest, Disco, Renesas), Netherlands (ASML, ASM International, BE Semiconductor), and Germany & France (Infineon, STMicroelectronics).

#### Scenario: All cards
- **WHEN** the user opens the view while connected
- **THEN** all 5 cards and 12 stock rows show, each with its value or the reason it has none

#### Scenario: Home listings
- **WHEN** a company also trades in the US
- **THEN** it shows its home listing in local currency, not the US listing

#### Scenario: Narrow window
- **WHEN** the window is too narrow for the content to fit side by side
- **THEN** index cards wrap to fewer columns in the same order, the table scrolls inside its own frame, and the page doesn't scroll sideways

### Requirement: Card contents
Each index card SHALL show the name, the last value, the change and percent change since the previous close, an intraday sparkline, whether the market is open or closed, and the local time of the latest data. Each chip stock row SHALL show the same figures in local currency, along with its market, without a sparkline.

#### Scenario: Time of the data
- **WHEN** the latest bar for the Nikkei 225 is from 09:15 Tokyo time
- **THEN** the card says so, because foreign data can lag by different amounts

#### Scenario: Market closed
- **WHEN** a market is closed
- **THEN** its card or row shows it as closed with the last session's value and change

#### Scenario: Comparing stocks
- **WHEN** the user reads the table
- **THEN** percent change has its own column, because the stocks trade in different currencies

### Requirement: Previous close
The change SHALL be measured against the last daily close from before the instrument's current session, not the last intraday bar, because closing auctions can set a different price.

#### Scenario: Closing auction
- **WHEN** the last 5-minute bar and the daily close differ
- **THEN** the change uses the daily close

### Requirement: Data refresh
Intraday data SHALL refresh every 5 minutes for instruments whose market is open. A closed market SHALL NOT be requested again until it reopens, once its final data is in. Daily closes SHALL refresh when an instrument's session changes. The view SHALL update without reloading.

#### Scenario: Only Asia is open
- **WHEN** Asia is open and Europe is closed
- **THEN** only Asian instruments are requested

#### Scenario: Holiday
- **WHEN** a market is closed for a holiday on a weekday
- **THEN** IBKR's trading hours show it as closed, and it isn't requested

### Requirement: Errors and disconnection
When IBKR refuses data for an instrument, its card or row SHALL show the IBKR error and the others SHALL keep updating, retrying every 5 minutes. When IBKR is disconnected, the view SHALL say so and keep the last values, marked as stale.

#### Scenario: Data refused
- **WHEN** IBKR refuses data for Infineon
- **THEN** that row shows the error, and the others keep updating

#### Scenario: Empty reply
- **WHEN** a refresh returns no bars
- **THEN** the card or row keeps its previous values

#### Scenario: Connection drops
- **WHEN** the IBKR connection drops
- **THEN** the view says it isn't connected, and cards and rows keep their last values marked as stale

### Requirement: Read-only and independent
The feature SHALL only read market data. It SHALL NOT place, modify, or cancel orders, SHALL NOT open market data lines or change the market data type, and SHALL NOT change signals, gamma, or the Macro view.

#### Scenario: While the view is in use
- **WHEN** data refreshes
- **THEN** only historical bars and contract details are requested

### Requirement: Delay shown
Each open instrument's card or table row SHALL show how many minutes behind its newest data is, measured from the end of its latest bar. Data under 2 minutes old SHALL show as current. A closed market SHALL show no delay.

#### Scenario: Delayed index
- **WHEN** the Nikkei 225's latest bar ended 17 minutes ago
- **THEN** its card says about 17 minutes behind

#### Scenario: Forming bar
- **WHEN** the latest bar hasn't ended yet
- **THEN** the data shows as current

#### Scenario: Closed market
- **WHEN** Amsterdam is closed
- **THEN** ASML's row shows no delay
