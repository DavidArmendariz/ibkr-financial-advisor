# Spec Delta

## MODIFIED Requirements

### Requirement: Instruments shown
The view SHALL show, in this order, an Indexes section (Nikkei 225, KOSPI 200, AEX, Euro Stoxx 50) as cards, and a Chip stocks section as one table in this market order: Korea (Samsung Electronics, SK Hynix), Taiwan (TSMC), Japan (Tokyo Electron, Advantest, Disco, Renesas), Netherlands (ASML, ASM International, BE Semiconductor), and Germany & France (Infineon, STMicroelectronics).

#### Scenario: All cards
- **WHEN** the user opens the view while connected
- **THEN** all 4 index cards and 12 stock rows show, each with its value or the reason it has none

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
