# Tasks

## 1. Readings

- [x] 1.1 Add `backend/rotation/` with pure functions for relative strength, RS-Ratio, RS-Momentum, quadrants, weekly bars from daily, and periods in a quadrant; test each, including a 100 boundary, the Friday week, and dropping a partial day
- [x] 1.2 Add a service fetching two years of daily bars for SPY and the 12 ETFs once per session, keeping the last readings on failure, and showing per-ETF errors; test caching, a refused ETF, a missing SPY, and disconnection
- [x] 1.3 Add `GET /api/rotation` with weekly and daily readings and the tail length, and settings persisted with a `ROTATION_` prefix; test them

## 2. View

- [x] 2.1 Add the Sector Rotation tab below Asia & Europe, with a hook, types, and API calls
- [x] 2.2 Build the SVG rotation graph with quadrant tints and names, muted trails, SMH highlighted, labelled heads, hover tooltips, and highlighting from the table
- [x] 2.3 Add the rotation table grouped by quadrant, the weekly and daily switch, the trail length, the approximation note, and stale and error states

## 3. Docs and verification

- [x] 3.1 Update the README and the capability list in `CLAUDE.md`
- [x] 3.2 Verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 3.3 Compare a few readings against the probe's live values, check the chart for overlapping labels, and look at it in a browser at full and narrow widths

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
