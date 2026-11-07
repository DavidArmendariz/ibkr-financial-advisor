# Proposal

## Why

The EMA cross only fires when the fast EMA crosses above the slow EMA, so it never flags bearish momentum. The user wants the opposite cross too.

A backtest of 180 cached SOXL sessions (1-minute bars, EMA 9/21, regular hours, current blackouts) found about 8 bearish crosses a day. After them, SOXL went up as often as after any minute: +0.015% after 15 minutes and +0.047% after 30, against +0.010% and +0.022% for every minute, with 48–49% down in each case. The upward cross showed no edge either. So the new trigger starts off, and outcome tracking will measure it on live alerts.

## What Changes

- A new **EMA cross down** trigger in the Technical category fires when the fast EMA crosses below the slow EMA, with its own switch, off by default, and its own cooldown.
- It shows as a downward marker on the chart, has its own notification and Signal History filter, and appears in the outcome table.
- Post-mortems judge it as a short entry.
- The existing EMA cross is unchanged, and its label says it's the upward cross.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `signal-alerts`: adds the EMA cross down trigger, and updates the default switches and the Signal History filter.
- `signal-analysis`: the post-mortem judges EMA cross down as a short entry.

## Impact

- **IBKR access:** unchanged. It uses bars already streamed.
- **Order handling:** not touched. It only alerts.
- **API keys:** not touched.
- **Data leaving the machine:** EMA cross down signals go to the AI provider only as other signals do, when the LLM filter is on or a post-mortem is requested.
- **Code:** `backend/signals/rules.py`, `config.py`, `analysis.py`, the Signals settings form, chart markers, Signal History filter, the post-mortem panel, types, README, tests.
