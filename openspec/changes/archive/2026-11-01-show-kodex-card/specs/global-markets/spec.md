# Spec Delta

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: KOSPI 200 estimate
**Reason**: The user doesn't want an estimated index value. The KODEX 200 card shows the current move directly.
**Migration**: Read the KODEX 200 card's percent change.
