# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`TRIGGERS` in `backend/signals/rules.py` lists each trigger with a signal type, category, setting, and test, and the pipeline evaluates each one with its own cooldown. `ema_cross` uses `crosses_above`, with the previous bar coming only from the same session. `analysis.directions_for` treats `LONG_TRIGGERS` as long and everything else as both directions. The post-mortem's figures are for a long entry, and the panel says a short is the opposite.

## Goals / Non-Goals

**Goals:**

- Flag bearish EMA crosses without changing the upward one.

**Non-Goals:**

- Combining it with other triggers, such as requiring price below VWAP. Triggers stay independent.
- Changing EMA periods or turning the trigger on by default.

## Decisions

### A separate trigger and switch

New signal type `EMA_CROSS_DOWN`, with setting `trigger_ema_down_enabled` (`SIGNALS_TRIGGER_EMA_DOWN_ENABLED`), defaulting to off.

- *Alternative: one switch for both directions, like the VWAP band.* Lost because the user would get ~8 extra alerts a day without asking, and the backtest found no edge to justify that.
- *Alternative: rename `EMA_CROSS` to `EMA_CROSS_UP`.* Lost because saved signals and outcomes use the existing name. Only its label changes.

### Judge it as a short

Add a short-trigger set to `directions_for`, and report the post-mortem figures for a short entry when that's the only direction.

- *Alternative: judge both directions.* Lost because a bearish cross implies one.

### A downward marker labelled EMA

It matches how VWAP band below and RSI below appear.

## IBKR dependencies

None. It uses the existing stream, and adds no requests.

## Risks / Trade-offs

- [Choppy sessions produce many crosses] → Off by default, with the shared cooldown setting limiting repeats.
- [No proven edge] → Stated in the proposal. Outcome tracking measures it once on.
