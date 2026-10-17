# app-navigation Specification

## Purpose

Lets the user move between the app's views through the sidebar, and hide the sidebar to give the current view the full window width.

## Requirements

### Requirement: Sidebar can be hidden
The system SHALL let the user hide the sidebar completely from a control in the sidebar, so the current view takes the full window width.

#### Scenario: Hide the sidebar
- **WHEN** the user clicks the hide control in the sidebar
- **THEN** the sidebar disappears and the current view widens to fill the window, keeping its contents and state

#### Scenario: Charts follow the new width
- **WHEN** the sidebar is hidden or shown while a chart is on screen
- **THEN** the chart resizes to the new width without a reload

### Requirement: Hidden sidebar can be restored
While the sidebar is hidden, the system SHALL show a top bar across the main view with a control that shows the sidebar again.

#### Scenario: Show the sidebar again
- **WHEN** the sidebar is hidden and the user clicks the show control in the top bar
- **THEN** the sidebar reappears with the same tab selected and the top bar goes away

#### Scenario: macOS window controls
- **WHEN** the sidebar is hidden in the macOS app
- **THEN** the top bar leaves room for the window buttons and the window can be dragged by it

### Requirement: Keyboard shortcut toggles the sidebar
The system SHALL toggle the sidebar with Cmd+B on macOS and Ctrl+B on other platforms.

#### Scenario: Toggle with the keyboard
- **WHEN** the user presses the shortcut
- **THEN** a shown sidebar hides, or a hidden one is shown

#### Scenario: Typing in a text field
- **WHEN** the user presses the shortcut while typing in the AI Advisor message box
- **THEN** the sidebar still toggles and no text is inserted

### Requirement: Sidebar state is remembered
The system SHALL remember whether the sidebar was hidden and restore that state the next time the app opens.

#### Scenario: Relaunch with the sidebar hidden
- **WHEN** the user hides the sidebar, quits and opens the app again
- **THEN** the app opens with the sidebar hidden

#### Scenario: First launch
- **WHEN** the app opens with no remembered state
- **THEN** the sidebar is shown
