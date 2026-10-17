# Spec Delta

## MODIFIED Requirements

### Requirement: Connection status is visible
The system SHALL show whether it is connected, and whether to the paper or live account, at all times.

#### Scenario: Connected to paper
- **WHEN** the app is connected to the paper port
- **THEN** the sidebar shows "Connected · Paper"

#### Scenario: Sidebar hidden
- **WHEN** the sidebar is hidden
- **THEN** the top bar shows the same connection status, such as "Connected · Live"
