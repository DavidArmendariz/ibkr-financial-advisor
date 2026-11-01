# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`IndicatorSet` updates each indicator on every bar, and `TRIGGERS` in `rules.py` lists independent checks that receive the settings. Per-type cooldowns, history, notifications, and analysis handle new signal types, and `directions_for` judges unlisted types in both directions.

Measured on 180 sessions of cached 1-minute bars, with a 5-minute cooldown, outside blackouts, per session:

| Period | Upper / lower | Above | Below | Total | Bars above upper |
|---:|---:|---:|---:|---:|---:|
| 14 | 70 / 30 | 4.0 | 3.8 | 7.8 | 15 |
| **14** | **75 / 25** | **1.5** | **1.6** | **3.1** | **5** |
| 14 | 80 / 20 | 0.4 | 0.5 | 0.9 | 1 |
| 14 | 85 / 15 | 0.1 | 0.1 | 0.2 | 0 |
| 7 | 70 / 30 | 12.5 | 11.9 | 24.4 | 47 |
| 7 | 80 / 20 | 4.3 | 4.2 | 8.5 | 12 |
| 21 | 70 / 30 | 1.5 | 1.5 | 2.9 | 6 |

## Goals / Non-Goals

**Goals:**

- A separate alert when RSI reaches a user-set level, in either direction.

**Non-Goals:**

- Separate switches or periods for each direction.
- An RSI line on the chart. It needs a separate 0–100 pane, because one chart must not have two scales.
- Divergence or other RSI patterns.
- Saying whether a reading means reversal or continuation. The alert states the level only.

## Decisions

### Wilder's RSI on closes

The first average is the simple mean of the first N gains and losses, and later ones use `(previous × (N−1) + current) / N`. RSI is `100 − 100 / (1 + average gain / average loss)`, and 100 when there are no losses. This matches common charting platforms.

- *Alternative: simple rolling averages (Cutler's RSI).* Lost because its numbers would differ from the charts traders compare with.

### Carry RSI across sessions, like the EMAs

- *Alternative: restart each session.* Lost because RSI would need 14 bars each morning, and with pre-market on it would miss early moves. It would also differ from charting platforms.

### Fire on the cross, not on every bar beyond

As with the other technical triggers, a cross needs the previous bar in the same session. At the defaults, RSI spends about 5 bars a session above the upper level, and the cross reports the event once.

- *Alternative: fire on every bar beyond the level.* Lost because it would repeat while RSI stays extreme.

### Default 14 periods, 75 and 25, trigger on

Period 14 is the convention. On 1-minute bars, 70/30 fires about 8 times a session, so 75/25 keeps it a notable event at about 3.

- *Alternative: 70/30.* Lost because of the noise on a 3x ETF's 1-minute bars. The user can set it.
- *Alternative: 80/20.* Lost because at under once a session, the trigger could go unnoticed.

### Two signal types behind one switch

`RSI_ABOVE` and `RSI_BELOW` follow the VWAP band pattern, each with its own cooldown, notification, and history filter.

- *Alternative: one type with a direction field.* Lost because cooldown and filters key on type.

### Levels apply live; the period rebuilds

`rsi_upper` and `rsi_lower` stay out of `pipeline_key()`. `rsi_period` joins it and `warmup_bars()`, because RSI state depends on it. Settings validation rejects a lower level at or above the upper one.

- *Alternative: treat the period like the levels.* Lost because changing it mid-stream would produce wrong values.

### Both directions in analysis

`directions_for` already treats unlisted types as both ways, so the code needs no change.

- *Alternative: treat RSI above as long.* Lost because a high RSI can mean strength or stretched.

## IBKR dependencies

None change. RSI uses the same real-time bars. With pre-market on, those bars feed RSI, and it has values at the open. Blackouts and market hours apply as for other triggers.

## Risks / Trade-offs

- [The alert could be read as buy or sell] → It states the level. An extreme can last, especially on a 3x ETF.
- [No RSI line on the chart] → Live values and alerts show the number, and a pane can follow if wanted.
- [Existing signals have no RSI] → The field is optional on the saved snapshot, and the notification omits it when absent.
- [The trigger has no backtested edge] → It's an alert, not a strategy. The summary states that.
