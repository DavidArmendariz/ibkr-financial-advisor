# Spec Delta

## Purpose

Lets the user look up a US stock's fundamentals in one view: its multiples against its peers and its own history, quality and growth, analyst ratings, recent news, and an optional AI write-up. Read-only: it raises no alerts and places no orders.

## ADDED Requirements

### Requirement: Fundamentals view in the sidebar
The sidebar SHALL list a Fundamentals item, directly below Sector Rotation, that opens a view with a ticker search.

#### Scenario: Open the view
- **WHEN** the user clicks Fundamentals in the sidebar
- **THEN** the view opens with a ticker field, and the item is shown as selected

#### Scenario: Unknown ticker
- **WHEN** the user looks up a ticker Finnhub doesn't know
- **THEN** the view says no US stock was found for it, and shows no figures

### Requirement: Valuation, quality, and growth
For the looked-up stock, the view SHALL show its name, industry, price, and market cap, and its P/E, P/S, EV/EBITDA, EV/FCF, and P/B on trailing figures, revenue and EPS growth, net and operating margins, ROE, and debt to equity. A figure that isn't available SHALL show as a dash, not zero.

#### Scenario: Loss-making company
- **WHEN** the company has negative earnings
- **THEN** its P/E shows as not meaningful rather than as a negative multiple

### Requirement: Comparison against peers
Each multiple SHALL be shown next to the median of the stock's peers, excluding the stock itself and repeated peers, with the peers listed. A multiple SHALL count as cheaper than peers when it's at least 20% below their median.

#### Scenario: Cheaper than peers
- **WHEN** a stock's EV/EBITDA is 12 and its peers' median is 20
- **THEN** the view marks EV/EBITDA as cheaper than peers

#### Scenario: Peers without the figure
- **WHEN** fewer than 3 peers report a multiple
- **THEN** that peer median shows as not enough peers

### Requirement: Comparison against its own history
Each multiple with a yearly history SHALL be shown next to its median over the last 5 fiscal years. A multiple SHALL count as cheaper than its history when it's at least 20% below that median.

#### Scenario: Below its usual multiple
- **WHEN** a stock's P/E is 18 and its 5-year median P/E is 25
- **THEN** the view marks P/E as cheaper than its history

#### Scenario: Short history
- **WHEN** a stock has fewer than 3 fiscal years of a multiple
- **THEN** that history median shows as not enough history

### Requirement: Analyst ratings
The view SHALL show the latest counts of strong buy, buy, hold, sell, and strong sell ratings, the share rating buy or strong buy, and the previous month's counts for comparison. It SHALL NOT show price targets.

#### Scenario: Ratings shift
- **WHEN** buy ratings rose since the previous month
- **THEN** both months' counts are shown, so the change is visible

### Requirement: Recent news
The view SHALL list recent headlines for the stock, newest first, from IBKR's news providers and from Finnhub, each with its time, source, and a link or a way to open it. If one source fails or IBKR isn't connected, the other's headlines SHALL still show, with a note.

#### Scenario: IBKR not connected
- **WHEN** IBKR is disconnected and the user looks up a stock
- **THEN** Finnhub headlines and all figures still show, with a note that IBKR news needs a connection

#### Scenario: Analyst action
- **WHEN** Briefing.com reports an upgrade for the stock
- **THEN** the headline appears with its source named

### Requirement: AI write-up
On request, the system SHALL send the stock's figures, comparisons, ratings, and headlines to the AI provider configured in Settings, and show a bull case, a bear case, a valuation view, and what to watch. The write-up SHALL be saved per ticker, shown with the date of its data, and replaced only when the user asks again.

#### Scenario: Write-up requested
- **WHEN** the user clicks the AI write-up button
- **THEN** the write-up appears and stays available the next time the user looks up that ticker

#### Scenario: Only public data is sent
- **WHEN** a write-up is requested
- **THEN** only that stock's public figures and headlines are sent, never positions, orders, or account data

#### Scenario: No provider configured
- **WHEN** no AI provider is configured
- **THEN** the button explains that a provider must be set in Settings, and the figures still show

### Requirement: Fundamentals data source and errors
The system SHALL use the Finnhub key saved in Calendar settings, kept in the backend. Without it, the view SHALL say so and link to the Calendar settings. A lookup SHALL be reused for an hour, unless the user refreshes it. If Finnhub limits or refuses requests, the view SHALL say so and keep any figures already shown.

#### Scenario: No Finnhub key
- **WHEN** no Finnhub key is saved
- **THEN** the view explains that the Finnhub key in Calendar settings is needed, with a link there

#### Scenario: Rate limited
- **WHEN** Finnhub answers that too many requests were made
- **THEN** the view asks the user to try again in a minute

### Requirement: Read-only
The Fundamentals view SHALL NOT raise alerts, change signals, or place, modify, or cancel orders. It SHALL say that the figures come from Finnhub and the write-up from an AI, and are not investment advice.

#### Scenario: Reading the view
- **WHEN** the user opens a stock
- **THEN** a note names the data sources and says the content is not investment advice
