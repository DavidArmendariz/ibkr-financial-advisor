# Tasks

## 1. Backend

- [x] 1.1 Add a shared delay function and return `delay_minutes` from Asia & Europe and Macro; test bars that ended, a forming bar, closed markets, and live cards
- [x] 1.2 Add KODEX 200 as a hidden instrument and return a KOSPI 200 estimate; test open, closed, older ETF data, and a missing ETF

## 2. View

- [x] 2.1 Show the estimate on the KOSPI 200 card, labelled, beside the real value
- [x] 2.2 Show the delay on Asia & Europe cards, table rows, and delayed Macro cards

## 3. Verification

- [x] 3.1 Update the README, and verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 3.2 Check the figures against real data and look at both views in a browser

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
