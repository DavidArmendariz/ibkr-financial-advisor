# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`SignalChart.tsx` builds one `lightweight-charts` 4.2.3 chart with candles, lines, and volume, and updates the forming candle every 5 seconds. Chart points already include `rsi` for each bar. Version 4 has no panes; they arrived in version 5. Its API does offer `subscribeVisibleLogicalRangeChange`, `setVisibleLogicalRange`, and `setCrosshairPosition`.

## Goals / Non-Goals

**Goals:**

- RSI under the price chart, aligned bar for bar.

**Non-Goals:**

- A configurable pane height, or hiding the pane.
- Other indicators in panes, or RSI on the live values update between bars.
- Upgrading the chart library.

## Decisions

### A second chart, synced to the first

A small chart in the same card holds the RSI line. Each chart's visible logical range drives the other, guarded so the two don't echo each other forever.

- *Alternative: upgrade to `lightweight-charts` 5 for native panes.* Lost because it changes the whole chart's API and risks regressions for one line.
- *Alternative: draw RSI on the price chart with its own scale.* Lost because the dataviz rules forbid two y-scales, and RSI would sit across the candles.

### Identical bar positions

Logical ranges are bar indexes, so both charts must hold the same bars. The RSI series includes every bar, with whitespace points for warmup bars, and the forming bar is added as a whitespace point too. Without that, the charts would drift by one bar during a session.

- *Alternative: sync by time range.* Lost because it can't express the empty space past the last bar, and it fails while the pane has fewer bars.

### Equal price scale width

Both right scales get the same `minimumWidth`, wide enough for chart prices, so the plot areas line up. The time axis shows only on the price chart's pane below it: the price chart hides its axis labels and the RSI pane shows them, keeping the time axis at the bottom of the card.

- *Alternative: keep both axes.* Lost because it repeats the same labels and wastes height.

### Fixed 0–100 scale

`autoscaleInfoProvider` returns 0 to 100, so RSI levels sit in the same place at any zoom.

- *Alternative: auto scale.* Lost because the levels and the line's meaning would shift as the user pans.

### Levels as price lines

`createPriceLine` draws dashed lines at `rsi_upper` and `rsi_lower`, replaced when settings change, in the muted axis color. The RSI line uses the existing blue chart color. Values stay in normal text, and each line carries a label, so identity isn't color alone.

- *Alternative: flat line series.* Lost because price lines are made for this, and don't add series or data.

### Crosshair sync through hover state

Each chart's crosshair move sets the other's with `setCrosshairPosition`, using a series value at that time, and clears it on leave. Both feed the existing hover readout.

- *Alternative: no crosshair sync.* Lost because reading RSI against a candle is the purpose of the pane.

## IBKR dependencies

None. The pane uses chart data that's already sent. Pacing and market hours are unaffected, and it updates when bars complete.

## Risks / Trade-offs

- [Sync loops between the two charts] → A guard flag ignores changes made by the other chart, and a test confirms the ranges settle.
- [Bars drifting apart during a session] → Whitespace points keep the counts equal, checked with a forming bar in the browser.
- [Extra height on the Signals view] → The pane is about 120 pixels, and the price chart keeps its size.
- [The pane's scale can't show the value between bars] → It updates when a bar completes, which matches when RSI alerts fire.
- [Old `lightweight-charts` behavior around whitespace with `setData`] → Covered by the browser checks.
