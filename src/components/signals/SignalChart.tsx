import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type LogicalRange,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fmtPrice } from './format'
import type { SignalBar, SignalChart as SignalChartData, SignalChartPoint, SignalRecord, SignalSettings } from '@/types'

const UP = '#34d399'
const DOWN = '#f87171'
const COLORS = {
  vwap: '#3987e5',
  emaFast: '#d95926',
  emaSlow: '#9085e9',
  bands: 'rgba(255,255,255,0.35)',
}
const SESSION_MINUTES = 390
const RSI_PANE_HEIGHT = 120
// Equal scale widths keep the two plot areas, and so the bars, lined up.
const PRICE_SCALE_WIDTH = 64
const CHART_THEME = {
  layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: 'rgba(255,255,255,0.5)' },
  grid: { vertLines: { color: 'rgba(255,255,255,0.04)' }, horzLines: { color: 'rgba(255,255,255,0.04)' } },
  crosshair: { mode: CrosshairMode.Normal },
}

const MARKER_TEXT: Record<string, string> = {
  VOLUME_SPIKE: 'VOL',
  EMA_CROSS: 'EMA',
  VWAP_CROSS: 'VWAP',
  VWAP_BAND_ABOVE: 'BAND',
  VWAP_BAND_BELOW: 'BAND',
  RSI_ABOVE: 'RSI',
  RSI_BELOW: 'RSI',
  LONG_ENTRY: 'LONG',
}

// Volume has no direction, so it sits above the bar as a dot rather than an up arrow.
function markerStyle(sig: SignalRecord) {
  const text = MARKER_TEXT[sig.signal_type] ?? sig.signal_type
  if (sig.signal_type === 'VWAP_BAND_BELOW' || sig.signal_type === 'RSI_BELOW') return { position: 'aboveBar', color: DOWN, shape: 'arrowDown', text } as const
  return sig.category === 'volume'
    ? ({ position: 'aboveBar', color: '#c98500', shape: 'circle', text } as const)
    : ({ position: 'belowBar', color: UP, shape: 'arrowUp', text } as const)
}

// lightweight-charts has no time zones: shift UTC seconds so the axis reads New York time.
const etFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  hourCycle: 'h23',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

function toChartTime(iso: string): UTCTimestamp {
  const date = new Date(iso)
  const p = Object.fromEntries(etFormatter.formatToParts(date).map((x) => [x.type, x.value]))
  const asIfUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second)
  return Math.floor(asIfUtc / 1000) as UTCTimestamp
}

type LineKey = 'vwap' | 'ema_fast' | 'ema_slow' | 'bb_upper' | 'bb_mid' | 'bb_lower'

function sameRange(a: LogicalRange | null, b: LogicalRange | null) {
  return !!a && !!b && Math.abs(a.from - b.from) < 0.01 && Math.abs(a.to - b.to) < 0.01
}

// Logical ranges are bar indexes, so a range from one chart only fits the other
// because both hold the same bars.
function syncRange(from: IChartApi, to: IChartApi) {
  const onChange = (range: LogicalRange | null) => {
    if (range && !sameRange(range, to.timeScale().getVisibleLogicalRange())) to.timeScale().setVisibleLogicalRange(range)
  }
  from.timeScale().subscribeVisibleLogicalRangeChange(onChange)
}

function line(points: SignalChartPoint[], key: LineKey | 'rsi') {
  return points.map((p) => (p[key] == null ? { time: toChartTime(p.time) } : { time: toChartTime(p.time), value: p[key] as number }))
}

interface Props {
  chart: SignalChartData | null
  forming: SignalBar | null
  signals: SignalRecord[]
  settings: SignalSettings | null
  symbol: string
}

export function SignalChart({ chart, forming, signals, settings, symbol }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rsiContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const rsiChartRef = useRef<IChartApi | null>(null)
  const rsiLevels = useRef<IPriceLine[]>([])
  const series = useRef<{
    candles: ISeriesApi<'Candlestick'>
    volume: ISeriesApi<'Histogram'>
    lines: Record<LineKey, ISeriesApi<'Line'>>
    rsi: ISeriesApi<'Line'>
  } | null>(null)
  const framed = useRef(false)
  const [hovered, setHovered] = useState<SignalChartPoint | null>(null)

  const bars = useMemo(() => chart?.bars ?? [], [chart])
  const byTime = useMemo(() => new Map(bars.map((b) => [toChartTime(b.time), b])), [bars])

  useEffect(() => {
    if (!containerRef.current || !rsiContainerRef.current) return
    const c = createChart(containerRef.current, {
      ...CHART_THEME,
      // The shared time axis sits under the RSI pane, at the bottom of the card.
      timeScale: { visible: false },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.06)', minimumWidth: PRICE_SCALE_WIDTH, scaleMargins: { top: 0.08, bottom: 0.22 } },
      width: containerRef.current.clientWidth,
      height: 380,
    })
    const band = { color: COLORS.bands, lineWidth: 1 as const, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }
    const lines = {
      bb_upper: c.addLineSeries(band),
      bb_lower: c.addLineSeries(band),
      bb_mid: c.addLineSeries({ ...band, lineStyle: LineStyle.Dotted }),
      vwap: c.addLineSeries({ color: COLORS.vwap, lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
      ema_slow: c.addLineSeries({ color: COLORS.emaSlow, lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
      ema_fast: c.addLineSeries({ color: COLORS.emaFast, lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
    }
    const volume = c.addHistogramSeries({ priceScaleId: 'volume', priceFormat: { type: 'volume' }, lastValueVisible: false, priceLineVisible: false })
    c.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })
    const candles = c.addCandlestickSeries({
      upColor: UP,
      downColor: DOWN,
      borderVisible: false,
      wickUpColor: UP,
      wickDownColor: DOWN,
    })
    const rsiChart = createChart(rsiContainerRef.current, {
      ...CHART_THEME,
      // The price chart above carries the TradingView attribution for the card.
      layout: { ...CHART_THEME.layout, attributionLogo: false },
      timeScale: { borderColor: 'rgba(255,255,255,0.06)', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.06)', minimumWidth: PRICE_SCALE_WIDTH, scaleMargins: { top: 0.06, bottom: 0.06 } },
      width: rsiContainerRef.current.clientWidth,
      height: RSI_PANE_HEIGHT,
    })
    const rsi = rsiChart.addLineSeries({
      color: COLORS.vwap,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      priceFormat: { type: 'price', precision: 0, minMove: 1 },
      // Fixed, so the levels stay put at any zoom.
      autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }),
    })
    syncRange(c, rsiChart)
    syncRange(rsiChart, c)
    series.current = { candles, volume, lines, rsi }
    chartRef.current = c
    rsiChartRef.current = rsiChart

    const ro = new ResizeObserver((entries) => {
      if (!entries[0]) return
      c.applyOptions({ width: entries[0].contentRect.width })
      rsiChart.applyOptions({ width: entries[0].contentRect.width })
    })
    ro.observe(containerRef.current)
    return () => {
      ro.disconnect()
      c.remove()
      rsiChart.remove()
      chartRef.current = null
      rsiChartRef.current = null
      rsiLevels.current = []
      series.current = null
    }
  }, [])

  // Hover readout uses the latest byTime map without recreating the chart.
  const byTimeRef = useRef(byTime)
  byTimeRef.current = byTime
  useEffect(() => {
    const c = chartRef.current
    const rsiChart = rsiChartRef.current
    const s = series.current
    if (!c || !rsiChart || !s) return
    // Moving one crosshair from the other chart fires its own move event.
    let mirroring = false
    const mirror = (apply: () => void) => {
      mirroring = true
      apply()
      mirroring = false
    }
    const onMove = (param: MouseEventParams<Time>, showOther: (time: Time, bar: SignalChartPoint) => void, clearOther: () => void) => {
      if (mirroring) return
      const bar = param.time ? byTimeRef.current.get(param.time as UTCTimestamp) ?? null : null
      setHovered(bar)
      mirror(() => (param.time && bar ? showOther(param.time, bar) : clearOther()))
    }
    const onPriceMove = (param: MouseEventParams<Time>) =>
      onMove(param, (time, bar) => rsiChart.setCrosshairPosition(bar.rsi ?? 50, time, s.rsi), () => rsiChart.clearCrosshairPosition())
    const onRsiMove = (param: MouseEventParams<Time>) =>
      onMove(param, (time, bar) => c.setCrosshairPosition(bar.close, time, s.candles), () => c.clearCrosshairPosition())
    c.subscribeCrosshairMove(onPriceMove)
    rsiChart.subscribeCrosshairMove(onRsiMove)
    return () => {
      c.unsubscribeCrosshairMove(onPriceMove)
      rsiChart.unsubscribeCrosshairMove(onRsiMove)
    }
  }, [])

  const rsiUpper = settings?.rsi_upper
  const rsiLower = settings?.rsi_lower
  useEffect(() => {
    const s = series.current
    if (!s) return
    for (const level of rsiLevels.current) s.rsi.removePriceLine(level)
    rsiLevels.current = [rsiUpper, rsiLower]
      .filter((price): price is number => price !== undefined)
      .map((price) =>
        s.rsi.createPriceLine({
          price,
          color: 'rgba(255,255,255,0.45)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          axisLabelColor: '#2a2a2e',
          axisLabelTextColor: 'rgba(255,255,255,0.8)',
          title: '',
        }),
      )
  }, [rsiUpper, rsiLower])

  useEffect(() => {
    const s = series.current
    if (!s) return
    s.candles.setData(bars.map((b) => ({ time: toChartTime(b.time), open: b.open, high: b.high, low: b.low, close: b.close })))
    s.volume.setData(
      bars.map((b) => ({
        time: toChartTime(b.time),
        value: b.volume,
        color: b.close >= b.open ? 'rgba(52,211,153,0.35)' : 'rgba(248,113,113,0.35)',
      })),
    )
    for (const key of Object.keys(s.lines) as LineKey[]) s.lines[key].setData(line(bars, key))
    s.rsi.setData(line(bars, 'rsi'))

    // Frame the latest session once; afterwards keep whatever the user has panned to.
    if (!framed.current && bars.length > 0 && chartRef.current) {
      const perSession = Math.round(SESSION_MINUTES / (chart?.timeframe_minutes ?? 1))
      chartRef.current.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - perSession), to: bars.length + 3 })
      framed.current = true
    }
  }, [bars, chart?.timeframe_minutes])

  useEffect(() => {
    const s = series.current
    const last = bars.at(-1)
    if (!s || !forming || (last && forming.time <= last.time)) return
    const time = toChartTime(forming.time)
    s.candles.update({ time, open: forming.open, high: forming.high, low: forming.low, close: forming.close })
    s.volume.update({ time, value: forming.volume, color: forming.close >= forming.open ? 'rgba(52,211,153,0.35)' : 'rgba(248,113,113,0.35)' })
    // RSI waits for the bar to complete, but the charts must keep the same bars.
    s.rsi.update({ time })
  }, [forming, bars])

  useEffect(() => {
    const s = series.current
    if (!s) return
    const minutes = chart?.timeframe_minutes ?? 1
    const first = bars[0]?.time
    const markers: SeriesMarker<Time>[] = signals
      .map((sig) => ({ sig, start: new Date(new Date(sig.time).getTime() - minutes * 60_000).toISOString() }))
      .filter(({ start }) => first !== undefined && start >= first)
      .map(({ sig, start }) => ({ time: toChartTime(start), ...markerStyle(sig) }))
      .sort((a, b) => a.time - b.time)
    s.candles.setMarkers(markers)
  }, [signals, bars, chart?.timeframe_minutes])

  const shown = hovered ?? bars.at(-1) ?? null
  const legend = [
    { label: 'VWAP', color: COLORS.vwap, value: shown?.vwap },
    { label: `EMA ${settings?.ema_fast ?? 9}`, color: COLORS.emaFast, value: shown?.ema_fast },
    { label: `EMA ${settings?.ema_slow ?? 21}`, color: COLORS.emaSlow, value: shown?.ema_slow },
    {
      label: `BB ${settings?.bb_period ?? 20}, ${settings?.bb_std ?? 2}σ`,
      color: COLORS.bands,
      value: null,
      text: shown?.bb_lower != null && shown?.bb_upper != null ? `${fmtPrice(shown.bb_lower)} – ${fmtPrice(shown.bb_upper)}` : '—',
    },
  ]

  return (
    <Card>
      <CardHeader className="flex flex-row items-baseline justify-between gap-4 pb-2">
        <CardTitle className="text-sm">
          {symbol} · {chart?.timeframe_minutes ?? 1}-min
        </CardTitle>
        {shown && (
          <span className="text-xs tabular-nums text-muted-foreground">
            O {fmtPrice(shown.open)} H {fmtPrice(shown.high)} L {fmtPrice(shown.low)} C {fmtPrice(shown.close)}
          </span>
        )}
      </CardHeader>
      <CardContent className="px-4 pb-3 pt-0">
        <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {legend.map((l) => (
            <span key={l.label} className="flex items-center gap-1.5">
              <span className="h-0.5 w-4 rounded" style={{ background: l.color }} />
              <span className="text-muted-foreground">{l.label}</span>
              <span className="tabular-nums text-foreground">{l.text ?? fmtPrice(l.value)}</span>
            </span>
          ))}
        </div>
        {bars.length === 0 && (
          <div className="flex h-24 items-center justify-center text-xs text-muted-foreground">
            The chart appears once market data is streaming.
          </div>
        )}
        <div ref={containerRef} className="w-full" />
        <div className="mb-1 mt-2 flex items-center gap-1.5 text-xs">
          <span className="h-0.5 w-4 rounded" style={{ background: COLORS.vwap }} />
          <span className="text-muted-foreground">RSI {settings?.rsi_period ?? 14}</span>
          <span className="tabular-nums text-foreground">{fmtPrice(shown?.rsi)}</span>
        </div>
        <div ref={rsiContainerRef} className="w-full" />
      </CardContent>
    </Card>
  )
}
