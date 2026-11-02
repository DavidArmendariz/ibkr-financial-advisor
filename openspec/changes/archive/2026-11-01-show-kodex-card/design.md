# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

## Goals / Non-Goals

**Goals:**

- The ETF is visible, and the official index card stays official.

**Non-Goals:**

- Cards for other ETFs.

## Decisions

### Remove the estimate

The ETF's own percent change gives the same read without a number that looks official.

- *Alternative: keep it on the ETF's card.* Lost because the user rejected it after seeing it.

### Send the unit from the backend

Index cards say pts, while the ETF says KRW, so the renderer can't derive it from the section.

- *Alternative: a separate section for the ETF.* Lost because it belongs next to the index.

## IBKR dependencies

None. Requests are unchanged.

## Risks / Trade-offs

- [A fifth card in the section] → Accepted, as the user asked for it.
