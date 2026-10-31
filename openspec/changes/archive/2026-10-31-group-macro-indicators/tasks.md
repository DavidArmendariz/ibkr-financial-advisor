# Tasks

## 1. Layout definition and shared pieces

- [x] 1.1 Add `src/components/macro/sections.ts` with the three sections and each card's indicator keys; verify `npx tsc --noEmit -p .` passes
- [x] 1.2 Move the label, freshness row, and error row out of `IndicatorCard.tsx` into shared components; verify in the browser that the crude, VIX, and USD/COP cards look unchanged

## 2. Index cards and sections

- [x] 2.1 Add `src/components/macro/IndexCard.tsx` with futures value, change, contract, and sparkline, plus a spot line with its own value, change, freshness, last update, and error; verify with mocked `/api/macro/state` responses in Playwright for both sides present, an error on the spot side, and no value on the futures side
- [x] 2.2 Update `src/pages/Macro.tsx` to render labelled sections from `sections.ts`, with unlisted indicators in a final "Other" section; verify with Playwright that the section order, card order, and "Other" section are right
- [x] 2.3 Verify stale handling with a mocked disconnected state in Playwright: the cards keep their values, and both sides of an index card are marked as stale
- [x] 2.4 Update the Macro features in `README.md` to describe the sections and combined cards; verify the indicator list still names all 11

## 3. Integration checks

- [x] 3.1 Run `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build`, and verify all pass
- [x] 3.2 Look at the Macro view with real data at http://localhost:5273, with screenshots kept in the scratchpad, at normal width, at a narrow width, and with the sidebar hidden, and verify nothing scrolls sideways
- [x] 3.3 Confirm no file under `backend/` changed, using `git status --short backend/`

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
