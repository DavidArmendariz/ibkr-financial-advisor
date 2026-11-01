# Tasks

## 1. Calculation

- [x] 1.1 Add pure functions to new `backend/macro/sentiment.py` for moving averages, returns, the five components, percentile scoring, the average, and bands, with no `pandas`; verify in new `tests/test_sentiment.py` with hand-worked series for the inverted VIX direction, top and bottom ranks, and every band edge
- [x] 1.2 Add partial-data handling and missing-history handling; verify with tests for four components, three components, two components with no score, and a symbol with too little history
- [x] 1.3 Compare the calculation with the prototype on the saved probe data; verify the latest score is within 0.5 of 24.0, explaining any difference, using `pandas` only in the test

## 2. Service and API

- [x] 2.1 Add a separate hourly sentiment task to `MacroService` that requests symbols one after another, rebuilds on connect, and records per-component errors, without touching indicator slots; verify with fake IBKR tests for a refused symbol, a reconnect, and the timer
- [x] 2.2 Add the `sentiment` field to `/api/macro/state`, with stale marking when disconnected; verify with a test and a request to the running backend, and that existing fields don't change

## 3. Renderer and docs

- [x] 3.1 Add the types and `src/components/macro/SentimentCard.tsx` with score, band, components, 60-day history, data date, error states, and the statement that it isn't CNN's index, using the dataviz skill's rules; verify `npx tsc --noEmit -p .` passes
- [x] 3.2 Show the card above the sections in `src/pages/Macro.tsx`; verify with Playwright and mocked states for a full score, a partial score, no score, and stale, and that sections still render without `sentiment`
- [x] 3.3 Update the README's Macro features, market data notes, and API reference; verify the wording against the code

## 4. Integration checks

- [x] 4.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 4.2 Check that `pandas` isn't imported by anything under `backend/`, using a search, so the packaged app can't break on it
- [x] 4.3 Look at the Macro view with real data at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths and with the sidebar hidden

## 5. Explanation

- [x] 5.1 Add a `meaning` to each component, and a closed-by-default How it's calculated section to `SentimentCard.tsx`, with the method, bands, and each component's calculation and meaning; verify with a test that every component has one, and with Playwright that it opens and closes at normal and narrow widths

## 6. Breadth as context

- [x] 6.1 Mark breadth as context only, leave it out of the score and history, and label it on the card and in the explanation; verify with tests that changing breadth doesn't change the score, that three scored components still give a score and two don't, and with a browser check of the card

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
