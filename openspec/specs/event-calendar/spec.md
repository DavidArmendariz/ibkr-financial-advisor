# event-calendar Specification

## Purpose

Shows upcoming economic releases and chip earnings that can move SOXL, and warns the user before they happen. Information only; events don't change signals, and no orders are placed.

## Requirements

### Requirement: Calendar view
The sidebar SHALL list a Calendar item, between Macro and Settings, that opens a view of upcoming events for the next 30 days, soonest first and grouped by day, each with its time in ET, name, category, and importance.

#### Scenario: Open the Calendar view
- **WHEN** the user clicks Calendar in the sidebar
- **THEN** the view opens with the next events first, and the Calendar item is shown as selected

#### Scenario: Unknown time
- **WHEN** an event has no known time
- **THEN** it shows its date without a time

#### Scenario: Works without IBKR
- **WHEN** IBKR isn't connected and the lock screen isn't showing
- **THEN** events still show, because they don't come from IBKR

### Requirement: Economic events
The calendar SHALL include FOMC rate decisions from the Federal Reserve's meeting calendar, and CPI, PPI, the jobs report, GDP, PCE, and retail sales from FRED's official release dates. FOMC, CPI, and the jobs report SHALL be marked high importance.

#### Scenario: FOMC meeting
- **WHEN** the Federal Reserve lists a two-day meeting
- **THEN** the event falls on the last day at 14:00 ET

#### Scenario: Release time
- **WHEN** the source gives a release date without a time
- **THEN** the event uses that release's usual time in ET

### Requirement: Earnings events
The calendar SHALL include earnings dates for a watchlist editable in settings, defaulting to NVDA, TSM, AVGO, AMD, ASML, MU, INTC, QCOM, AMAT, and LRCX, marked before the open or after the close when the source says so.

#### Scenario: Watchlist changed
- **WHEN** the user adds or removes a watchlist symbol
- **THEN** the change saves immediately, and the calendar lists earnings for the new symbols within a minute, without a restart

#### Scenario: After the close
- **WHEN** a company reports after the close
- **THEN** the event shows After close

#### Scenario: Symbol not covered
- **WHEN** the earnings source refuses one watchlist symbol, such as a foreign listing
- **THEN** the other symbols still update, and the view names the symbol it couldn't get

### Requirement: Calendar keys
Settings SHALL let the user save a FRED key and a Finnhub key, stored in the backend. The renderer SHALL only see whether each is set and a short hint. A missing key SHALL affect only that key's source, and the view SHALL say what's missing.

#### Scenario: No FRED key
- **WHEN** no FRED key is saved
- **THEN** the view still shows FOMC and earnings events, and says that a FRED key adds the economic releases

#### Scenario: Key not exposed
- **WHEN** the renderer reads settings
- **THEN** it receives only whether the key is set and its hint

### Requirement: Calendar refresh
The system SHALL refresh each source at least every 6 hours and save events locally. When a source fails, the system SHALL keep its saved events, show when it last updated and why it failed, and retry within an hour.

#### Scenario: Source down
- **WHEN** Finnhub can't be reached
- **THEN** saved earnings still show, with the error and the last update time

#### Scenario: After restart
- **WHEN** the app restarts without internet
- **THEN** saved events still show

### Requirement: Event alerts
The system SHALL send a desktop notification at 18:00 ET the evening before each high-importance event and each watchlist earnings date, and 30 minutes before each high-importance event with a known time. Each alert SHALL have an on/off switch, on by default.

#### Scenario: Evening before
- **WHEN** it's 18:00 ET the day before a CPI release
- **THEN** a notification names the event and when it happens

#### Scenario: Thirty minutes before
- **WHEN** an FOMC decision is 30 minutes away
- **THEN** a notification names it

#### Scenario: Unknown time
- **WHEN** an event has no known time
- **THEN** no 30-minute alert is sent

#### Scenario: Clicking an alert
- **WHEN** the user clicks an event notification
- **THEN** the Calendar view opens

### Requirement: Alerts fire once
Each alert SHALL fire at most once for an event, including across restarts. An alert missed while the app wasn't running SHALL be skipped, unless the event is still ahead and its alert time passed less than 30 minutes ago.

#### Scenario: Restart after an alert
- **WHEN** the app restarts after an alert fired
- **THEN** that alert doesn't fire again

#### Scenario: App closed at alert time
- **WHEN** the app starts 6 hours after an alert time
- **THEN** that alert is skipped

### Requirement: Calendar stays separate from trading
The calendar SHALL NOT change signals, alerts from triggers, or the LLM filter, and SHALL NOT request account data or place orders.

#### Scenario: Signal during an event
- **WHEN** a trigger fires during a CPI release
- **THEN** the signal behaves as usual
