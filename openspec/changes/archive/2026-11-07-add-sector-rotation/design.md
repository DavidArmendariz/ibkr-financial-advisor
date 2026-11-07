# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

The official JdK RS-Ratio and RS-Momentum formulas behind Relative Rotation Graphs are proprietary. A probe on Nov 6, 2026 through the live connection got 105 weekly and 251 daily bars for SPY and all 12 ETFs, and computed the approximation below with plausible results. Charts in the app use the dataviz palette, with categorical slots `#3987e5`, `#d95926`, `#199e70`, `#c98500`, and so on, and never more than 8 categorical hues.

## Goals / Non-Goals

**Goals:**

- See at a glance which sectors money is moving into and out of, and where semiconductors sit.

**Non-Goals:**

- Matching StockCharts' or TradingView's RRG values exactly.
- Choosing the benchmark or the ETFs, or adding individual stocks.
- Alerts when an ETF changes quadrant.
- Intraday readings.

## Decisions

### An open approximation of RS-Ratio and RS-Momentum

RS = 100 × ETF close ÷ SPY close. RS-Ratio = 100 + (RS − its 10-period mean) ÷ its 10-period standard deviation. RS-Momentum = 100 + the same normalisation, applied to the period-on-period change in RS-Ratio. Both centre on 100, so the quadrants split at 100 as in a standard RRG.

- *Alternative: a moving-average ratio, RS ÷ SMA(RS).* Lost because a z-score puts every ETF on a comparable scale.
- *Alternative: buy official RRG data.* Lost because it costs money and needs a third-party key, when an approximation gives the same picture.

### Weekly from daily bars

Daily bars are fetched once per session, and weeks are built from them, ending on Friday.

- *Alternative: request weekly bars too.* Lost because it doubles the requests, and the probe showed daily bars are enough.

### Completed sessions only

Today's bar is dropped until the close, as for daily ATR.

- *Alternative: a live intraday point.* Lost because a partial day makes the newest point jump around.

### A hand-drawn SVG chart

This keeps the dependency count down, and gives full control of tails, labels, and hover.

- *Alternative: lightweight-charts.* Lost because it only draws time series, not scatter plots.

### Colour for SMH only

Twelve series exceed the 8 categorical hues. All trails are a muted neutral with direct labels at their heads, SMH uses `#3987e5`, and hovering or selecting an ETF in the table highlights its trail. Quadrant names sit in the corners as text over faint tints, so meaning never depends on colour alone. A legend isn't needed, because every head is labelled.

- *Alternative: one hue per ETF.* Lost because that's 12 hues, beyond the palette's 8.
- *Alternative: colour by quadrant.* Lost because colour should follow the ETF, not its rank, or a trail would change colour as it moves.

### Fixed universe and benchmark

The 11 SPDR sectors cover the whole S&P 500, SMH covers what SOXL tracks, and SPY is the benchmark.

- *Alternative: configurable lists.* Lost because it adds settings before there's a need.

## IBKR dependencies

13 daily-bar requests per session, run one at a time, with the same Network B subscription as SOXL. Works with the market closed.

## Risks / Trade-offs

- [The readings differ from commercial RRG tools] → Labelled as an approximation.
- [Labels can overlap when ETFs cluster near 100] → Labels are offset, and the table always has exact values.
- [Rotation describes the past] → Context only, with no alerts.
