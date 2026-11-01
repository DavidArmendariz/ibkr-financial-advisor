# Proposal

## Why

The user wants a fear and greed reading in the Macro view. CNN's index has no official API and its data endpoint refuses automated requests, so the app can't show that number. A score built from the user's own IBKR data gives a similar reading with no scraping, and every input stays visible.

## What Changes

- Add a **Market Sentiment** card at the top of the Macro view, above the existing sections, with a 0–100 score and a band: Extreme Fear, Fear, Neutral, Greed, or Extreme Greed.
- The score averages four components, each scored by where it sits against its own past year:
  - **Momentum:** S&P 500 against its 125-day average.
  - **Volatility:** VIX against its 50-day average, inverted so high VIX means fear.
  - **Safe haven demand:** 20-day return of SPY minus TLT.
  - **Junk bond demand:** HYG/LQD against its 50-day average.
- **Breadth** (RSP/SPY against its 50-day average) is shown on the card as context only and doesn't affect the score.
- The card shows each component's score, the score's last 60 days, and the date of the data.
- The card states it's the app's own estimate and not CNN's Fear & Greed Index.
- A **How it's calculated** section explains the method, the bands, and what each component means.
- The score uses daily closes, so it changes once a day after the close.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `macro-indicators`: adds the Market Sentiment card and its calculation. Existing requirements don't change.

## Impact

- **IBKR access:** adds read-only daily historical requests for SPX, VIX, SPY, TLT, HYG, LQD, and RSP. A test run on the user's paper account returned three years for all seven. No streaming lines are used.
- **Order handling:** not touched.
- **API keys:** not touched.
- **Data leaving the machine:** none. The score is computed locally, and CNN isn't contacted.
- **Code:** new `backend/macro/sentiment.py`, `backend/macro/service.py`, new `src/components/macro/SentimentCard.tsx`, `src/pages/Macro.tsx`, `src/types/index.ts`, `README.md`, new backend tests.
- **API:** `GET /api/macro/state` gains a `sentiment` field. Existing fields don't change.
