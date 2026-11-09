# Spec Delta

## MODIFIED Requirements

### Requirement: Planner never places orders
The planner's calculations SHALL NOT place, modify, or cancel orders by themselves. The planner SHALL hand its entry, stop, target, and share count to order entry on the same view, which places orders only after review and confirmation.

#### Scenario: Using a plan
- **WHEN** the user has a plan on screen
- **THEN** the planner's own actions are editing inputs, copying values, and opening a review in order entry, and no order is sent without confirming that review
