# Tasks

## 1. ATR indicator

- [x] 1.1 Add Wilder's ATR to `IndicatorSet` and `IndicatorValues`, with `atr_period` (default 14) in Signals settings; test against a pandas calculation, the warm-up, and a gap between sessions
- [x] 1.2 Show ATR in the Signals live values, and the period in the Signals settings

## 2. Planner backend

- [x] 2.1 Add `backend/planner/` with pure functions for the plan, ATR from bars, and risk; test the spec's example, rounding down, risk from net liquidation, the available funds warning, and invalid inputs
- [x] 2.2 Add `PLANNER_` settings with `save_env_values`, and a service fetching SOXS 1-minute bars while requested and daily bars per session; test a refused symbol and caching
- [x] 2.3 Add `GET /api/planner` and `PUT /api/planner/settings`, with tests, and confirm `tests/test_orders.py` still passes with no order calls
- [x] 2.4 Stream bid and ask for both symbols while the planner is requested, drop them after 2 idle minutes, and default the entry to the ask; test subscribing, the idle drop, a crossed or missing quote, and reconnecting

## 3. View

- [x] 3.1 Add the Trade Planner tab below Signal History, with the ATR cards, inputs, results, the available funds warning, the gap note, and Copy
- [x] 3.2 Update the README and the capability list in `CLAUDE.md`

## 4. Verification

- [x] 4.1 Verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 4.2 Check ATR values against another source on a few bars, check a plan by hand, and look at the view in a browser, including a narrow window

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
