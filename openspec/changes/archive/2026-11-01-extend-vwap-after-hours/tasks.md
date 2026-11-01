# Tasks

## 1. VWAP

- [x] 1.1 Extend `vwap_anchor` to 20:00 ET when extended hours are included; verify with tests for after-hours, regular-only data, the 20:00 end, and the next session's restart
- [x] 1.2 Confirm signals don't change, with a test that after-hours VWAP raises none and a replay of the cached 180 sessions before and after
- [x] 1.3 Update the README; verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass, and look at the chart with real data

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
