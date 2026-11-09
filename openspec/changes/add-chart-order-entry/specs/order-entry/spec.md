# Spec Delta

## Purpose

Lets the user place, modify, and cancel bracket orders for SOXL and SOXS from a chart, long or short, in every US session. The app picks the order structure IBKR allows in each session, and confirmation and limit safeguards guard every order.

## ADDED Requirements

### Requirement: Chart with draggable levels
The Trade Planner view SHALL show a candle chart for the selected symbol, including extended hours, with draggable entry, stop loss, and take profit lines. They start from the planner's values. Dragging a line SHALL update the planner's entry, stop, target, and share count from its risk setting. A stop on the wrong side of the entry for the chosen direction SHALL block review.

#### Scenario: Drag the stop
- **WHEN** the user drags the stop line lower on a long plan
- **THEN** the stop price, the risk per share, and the share count update to match

#### Scenario: Stop on the wrong side
- **WHEN** a long plan's stop is dragged above its entry
- **THEN** review is disabled with a message saying the stop must be below the entry

### Requirement: Long and short
The user SHALL choose long or short for SOXL or SOXS. A long plan buys with the stop below and the target above the entry. A short plan sells short with the stop above and the target below.

#### Scenario: Short SOXS
- **WHEN** the user plans a short SOXS trade
- **THEN** the entry is a sell, the stop is a buy above the entry, and the take profit is a buy below it

### Requirement: Review before sending
Before any order is sent, the system SHALL show a review with the account and whether it is PAPER or LIVE, the symbol, direction, shares, every order to be sent with its type and session, the risk and reward in dollars, and IBKR's commission and margin preview. Orders SHALL be sent only when the user confirms that review, within 2 minutes.

#### Scenario: Confirm
- **WHEN** the user confirms a review
- **THEN** exactly the orders shown are sent, and the bracket appears on the chart with its status

#### Scenario: Stale review
- **WHEN** the user confirms more than 2 minutes after the review, or after the plan or account changed
- **THEN** nothing is sent and the user is asked to review again

### Requirement: Protection in pre-market, regular hours, and after-hours
Between 4:00 and 20:00 ET, the system SHALL send a native IBKR bracket: a limit entry, a stop-limit stop, and a take-profit limit, all allowed outside regular hours, so that one exit filling cancels the other at IBKR. The stop-limit's limit SHALL sit past the trigger by the gap cap percentage.

#### Scenario: Bracket in after-hours
- **WHEN** the user confirms a long SOXL trade at 17:00 ET
- **THEN** IBKR holds a buy limit, a sell stop-limit, and a sell limit, linked so a fill on one exit cancels the other, active outside regular hours

### Requirement: Protection overnight
Between 20:00 and 3:50 ET, the system SHALL send the entry and the take profit as limit orders on IBKR's overnight venue, and SHALL watch the stop itself. The view SHALL say that this stop protects the position only while the app and TWS are running and connected. A position still open at 20:00 SHALL get the same overnight protection. When the session ends, protection SHALL pass to the 4:00–20:00 bracket orders.

#### Scenario: Overnight plan
- **WHEN** the user reviews a trade at 22:00 ET
- **THEN** the review lists the overnight limit entry and take profit, and an app-watched stop, with the warning about staying connected

#### Scenario: Held into the night
- **WHEN** a bracket placed at 11:00 ET is still open at 20:00 ET
- **THEN** a take profit is placed on the overnight venue and the app starts watching the stop

#### Scenario: Session hand-off
- **WHEN** a position protected overnight reaches 3:50 ET
- **THEN** a stop-limit and a take profit active outside regular hours are working at IBKR before the 4:00 session opens

### Requirement: App-watched stop
When the price crosses an app-watched stop, the system SHALL cancel the take profit and send a limit to exit at the gap cap past the bid (long) or ask (short), 1% by default. It SHALL notify the user, and notify again if the exit hasn't filled within 1 minute. Watched stops SHALL be saved, so they resume after a restart or reconnection.

#### Scenario: Stop crossed overnight
- **WHEN** SOXL's bid falls through a long position's watched stop at 01:00 ET
- **THEN** the take profit is cancelled, a sell limit 1% below the bid is sent, and a notification says so

#### Scenario: App restarted
- **WHEN** the app restarts while a watched stop is active
- **THEN** the stop is watched again as soon as IBKR reconnects, and the view shows the time it wasn't being watched

### Requirement: Modify and cancel
The working stop and target of a bracket placed by the app SHALL show on the chart. Dragging one, or cancelling the bracket, SHALL show a review and SHALL change orders only after confirmation.

#### Scenario: Move the take profit
- **WHEN** the user drags a working take profit higher and confirms
- **THEN** the order at IBKR is modified to the new price, and nothing else changes

### Requirement: Order safeguards
Live orders SHALL be refused unless live trading is switched on in Settings, which is off by default. Any order whose value exceeds the per-order cap in Settings SHALL be refused. A live review SHALL be visibly distinct and name the live account. Orders SHALL only be sent from the order entry feature, and never from signals, analyses, or other views.

#### Scenario: Live off
- **WHEN** the app is connected to live and live trading is off
- **THEN** review is disabled with a message pointing to the Settings switch

#### Scenario: Over the cap
- **WHEN** a plan's value exceeds the per-order cap
- **THEN** review is refused with the cap and the plan's value shown

### Requirement: Order errors
If IBKR rejects or doesn't confirm an order, the system SHALL show IBKR's message. It SHALL NOT retry on its own. If an exit order is rejected after the entry filled, it SHALL warn that the position is unprotected.

#### Scenario: Exit rejected after the fill
- **WHEN** IBKR rejects the take profit after the entry filled
- **THEN** a warning says the position has no take profit, with IBKR's reason, and a notification is sent
