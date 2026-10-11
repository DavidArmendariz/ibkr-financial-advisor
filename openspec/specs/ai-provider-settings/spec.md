# ai-provider-settings Specification

## Purpose

Lets the user choose and configure the AI provider used by every AI feature, while keeping API keys out of the user interface.

## Requirements

### Requirement: Provider choice
The system SHALL let the user choose between Anthropic and an OpenAI-compatible endpoint (OpenRouter, OpenAI, or a local server such as Ollama or LM Studio). The choice SHALL apply to every AI feature.

#### Scenario: Switching provider
- **WHEN** the user selects a different provider in Settings
- **THEN** the AI Advisor and the signal LLM filter both use it from the next request

### Requirement: Keys are verified before saving
The system SHALL verify an API key or endpoint with the provider before saving it, and SHALL report a clear error when verification fails.

#### Scenario: Rejected key
- **WHEN** the user saves an Anthropic key that Anthropic rejects
- **THEN** the key is not saved and Settings shows that the key was rejected

### Requirement: Keys never reach the user interface
API keys SHALL be stored only on the local machine with owner-only file permissions. The user interface SHALL only ever receive whether a key is set and its last four characters.

#### Scenario: Viewing settings
- **WHEN** the Settings view loads
- **THEN** it shows "…abcd"-style hints and never the stored key
