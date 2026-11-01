# Tasks

## 1. RSI pane

- [x] 1.1 Add the second chart to `SignalChart.tsx` with an RSI line on a fixed 0–100 scale, whitespace for bars without RSI, matching right scale width, and the time axis at the bottom; verify in the browser with real data that bars line up with the candles
- [x] 1.2 Add dashed lines for the upper and lower levels that follow the settings; verify with Playwright that saving new levels moves them without a reload, using mocked saves
- [x] 1.3 Sync the visible range both ways, with a guard against loops; verify with Playwright that zooming each chart moves the other, and that the ranges settle
- [x] 1.4 Sync the crosshair and add the RSI period and value to the legend; verify with Playwright that hovering either chart updates both
- [x] 1.5 Add a whitespace point for the forming bar and extend the line as bars complete; verify with Playwright and mocked socket messages that alignment holds through a forming bar and a completed one

## 2. Docs

- [x] 2.1 Update the README's Signals features and the design note on the chart; verify the wording against the view

## 3. Integration checks

- [x] 3.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 3.2 Look at the Signals view in a browser at http://localhost:5273, with screenshots kept in the scratchpad, at normal and narrow widths and with the sidebar hidden, including that resizing keeps both charts aligned
- [x] 3.3 Confirm `.env` is unchanged after testing

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
