# Proposal

## Why

The KOSPI 200 card runs about 20 minutes behind Samsung and SK Hynix, so the index and its largest stocks can seem to disagree. Delayed data elsewhere is labelled only as delayed or by a time, so the user has to work out how far behind it is.

## What Changes

- While Korea is open, the KOSPI 200 card shows an estimated current value from the KODEX 200 ETF, clearly labelled, beside the real index value.
- Asia & Europe cards and table rows show how far behind their data is.
- Macro cards with delayed data show how far behind they are.
- The delay is measured from the newest bar, not a fixed figure.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `global-markets`: adds the KOSPI 200 estimate and the delay shown per instrument.
- `macro-indicators`: adds the delay shown on delayed cards.

## Impact

- **IBKR access:** read-only. Adds historical bar requests for one ETF.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none.
- **Code:** `backend/global_markets/`, `backend/macro/`, Asia & Europe and Macro components, types, README, `tests/`.
