# app-lifecycle Specification

## Purpose

Keeps the desktop app and its local backend starting, running, and stopping cleanly, so no background process is left holding the app's port.

## Requirements

### Requirement: Backend stops with the app
When the packaged app quits, the system SHALL ask its backend to stop and SHALL force it to stop if it has not exited within 5 seconds.

#### Scenario: Backend hangs on quit
- **WHEN** the user quits and the backend does not respond
- **THEN** the app exits within about 5 seconds and the backend is no longer running

### Requirement: Recovery from a crashed run
On launch, the packaged app SHALL stop a backend left running by a previous crashed or force-quit run, and only if that process is still the app's own backend.

#### Scenario: Previous run crashed
- **WHEN** the app is launched after a crash left its backend running
- **THEN** the old backend is stopped and a new one starts on the same port

### Requirement: Bounded backend shutdown
The backend SHALL finish shutting down within about 5 seconds even if requests or live connections are still open.

#### Scenario: Request waiting on IBKR
- **WHEN** the backend is stopped while a request is still waiting for IBKR
- **THEN** that request is cancelled and the backend exits

### Requirement: User data survives updates
Settings, API keys, chat history, signal history, and cached option data SHALL live in the user's data folder, which SHALL stay the same across app updates and the rename to DeltaAdvisor.

#### Scenario: After an update
- **WHEN** the user installs a newer build
- **THEN** their saved API key and conversations are still present
