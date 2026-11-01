# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`SessionCalendar.vwap_anchor` returns the session's start only until the regular close, so `SessionVWAP` yields nothing afterwards.

## Goals / Non-Goals

**Goals:**

- A continuous VWAP line through after-hours.

**Non-Goals:**

- Any change to triggers, the volume profile, or regular-hours values.
- A setting to turn it off.

## Decisions

### Continue the same session's total

After-hours bars add to the session's running VWAP, which restarts at 04:00 ET.

- *Alternative: a separate after-hours VWAP from 16:00.* Lost because the user asked for the line to continue.

### Tie it to `include_premarket`

That setting already controls whether extended-hours bars are requested, so no new setting is needed.

- *Alternative: a separate setting.* Lost because without extended bars there's nothing to draw.

### End at 20:00 ET

- *Alternative: use the exchange's listed extended hours.* Lost because bars simply stop on half-days, so a fixed end is enough.

## IBKR dependencies

None. The bars are already streamed, and pacing is unaffected. After-hours volume is thin, so the line barely moves after the close.

## Risks / Trade-offs

- [Thin volume gives a flat line] → Expected, and harmless.
- [`ready()` is now true after the close] → Triggers stay blocked by the blackout check, confirmed by replaying 180 sessions with identical signals.
