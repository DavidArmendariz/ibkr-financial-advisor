# Spec Delta

## ADDED Requirements

### Requirement: Delay shown on delayed cards
A card marked Delayed SHALL show how many minutes behind its data is, measured from the end of its latest 5-minute bar. Live and closed cards SHALL NOT show a delay.

#### Scenario: Delayed futures
- **WHEN** S&P 500 futures are delayed and their latest bar ended 10 minutes ago
- **THEN** the card says about 10 minutes behind

#### Scenario: Live data
- **WHEN** a subscription makes a card Live
- **THEN** it shows no delay

#### Scenario: No bars yet
- **WHEN** a delayed card has no bars
- **THEN** it says Delayed without a figure
