import { useEffect, useRef } from 'react'
import { ColorType, CrosshairMode, LineStyle, createChart, type IChartApi, type IPriceLine, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts'
import type { OHLCBar } from '@/types'

export interface ChartLine {
  id: string
  role: 'entry' | 'stop' | 'target'
  price: number
  label: string
  draggable: boolean
  working: boolean // a live order at IBKR, drawn solid; a draft is dashed
}

interface Props {
  bars: OHLCBar[]
  bid: number | null
  ask: number | null
  lines: ChartLine[]
  onDrag: (id: string, price: number) => void
  onDragEnd: (id: string, price: number) => void
}

// Identity is carried by the line's label as well as its colour.
const ROLE_COLOR = { entry: '#3987e5', stop: '#d95926', target: '#199e70' }
const GRAB_PX = 7
const UP = '#34d399'
const DOWN = '#f87171'

const etFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
})

// lightweight-charts shows times as UTC, so bars are shifted to read as ET.
function toChartTime(unixSeconds: number): UTCTimestamp {
  const p = Object.fromEntries(etFormatter.formatToParts(new Date(unixSeconds * 1000)).map((x) => [x.type, x.value]))
  return (Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute, +p.second) / 1000) as UTCTimestamp
}

const snap = (price: number) => Math.round(price * 100) / 100

export function OrderChart({ bars, bid, ask, lines, onDrag, onDragEnd }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const priceLines = useRef<IPriceLine[]>([])
  const linesRef = useRef(lines)
  const dragging = useRef<string | null>(null)
  const handlers = useRef({ onDrag, onDragEnd })
  linesRef.current = lines
  handlers.current = { onDrag, onDragEnd }

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const chart = createChart(el, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: 'rgba(255,255,255,0.5)' },
      grid: { vertLines: { color: 'rgba(255,255,255,0.04)' }, horzLines: { color: 'rgba(255,255,255,0.04)' } },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { timeVisible: true, secondsVisible: false, rightOffset: 8 },
      rightPriceScale: { borderVisible: false },
      autoSize: true,
    })
    const series = chart.addCandlestickSeries({
      upColor: UP, downColor: DOWN, wickUpColor: UP, wickDownColor: DOWN, borderVisible: false,
      // Keep every order line in view, even far from the candles.
      autoscaleInfoProvider: (original: () => { priceRange: { minValue: number; maxValue: number } } | null) => {
        const res = original()
        const prices = linesRef.current.map((l) => l.price)
        if (!res || prices.length === 0) return res
        return { ...res, priceRange: { minValue: Math.min(res.priceRange.minValue, ...prices), maxValue: Math.max(res.priceRange.maxValue, ...prices) } }
      },
    })
    chartRef.current = chart
    seriesRef.current = series

    const near = (y: number) => {
      let best: { id: string; dist: number } | null = null
      for (const l of linesRef.current) {
        if (!l.draggable) continue
        const ly = series.priceToCoordinate(l.price)
        if (ly === null) continue
        const dist = Math.abs(ly - y)
        if (dist <= GRAB_PX && (!best || dist < best.dist)) best = { id: l.id, dist }
      }
      return best?.id ?? null
    }
    const localY = (e: PointerEvent) => e.clientY - el.getBoundingClientRect().top

    const down = (e: PointerEvent) => {
      const id = near(localY(e))
      if (!id) return
      dragging.current = id
      el.setPointerCapture(e.pointerId)
      // Freeze the price axis: re-fitting it to the moving line would shift prices under the pointer.
      chart.applyOptions({ handleScroll: false, handleScale: false })
      chart.priceScale('right').applyOptions({ autoScale: false })
      e.preventDefault()
    }
    const move = (e: PointerEvent) => {
      const y = localY(e)
      if (dragging.current) {
        const price = series.coordinateToPrice(y)
        if (price !== null && price > 0) handlers.current.onDrag(dragging.current, snap(price))
        return
      }
      el.style.cursor = near(y) ? 'ns-resize' : ''
    }
    const up = (e: PointerEvent) => {
      if (!dragging.current) return
      const id = dragging.current
      dragging.current = null
      el.releasePointerCapture(e.pointerId)
      chart.applyOptions({ handleScroll: true, handleScale: true })
      chart.priceScale('right').applyOptions({ autoScale: true })
      const price = series.coordinateToPrice(localY(e))
      const line = linesRef.current.find((l) => l.id === id)
      handlers.current.onDragEnd(id, price !== null && price > 0 ? snap(price) : line?.price ?? 0)
    }
    el.addEventListener('pointerdown', down)
    el.addEventListener('pointermove', move)
    el.addEventListener('pointerup', up)
    el.addEventListener('pointercancel', up)
    return () => {
      el.removeEventListener('pointerdown', down)
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerup', up)
      el.removeEventListener('pointercancel', up)
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) return
    const seen = new Set<number>()
    const data = bars
      .map((b) => ({ time: toChartTime(b.time), open: b.open, high: b.high, low: b.low, close: b.close }))
      .filter((b) => (seen.has(b.time) ? false : (seen.add(b.time), true)))
    series.setData(data)
  }, [bars])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) return
    for (const l of priceLines.current) series.removePriceLine(l)
    priceLines.current = []
    const add = (price: number, color: string, title: string, style: LineStyle, width: 1 | 2) =>
      priceLines.current.push(series.createPriceLine({ price, color, title, lineStyle: style, lineWidth: width, axisLabelVisible: true }))
    if (bid !== null) add(bid, 'rgba(255,255,255,0.35)', 'Bid', LineStyle.Dotted, 1)
    if (ask !== null) add(ask, 'rgba(255,255,255,0.35)', 'Ask', LineStyle.Dotted, 1)
    for (const l of lines) add(l.price, ROLE_COLOR[l.role], l.label, l.working ? LineStyle.Solid : LineStyle.Dashed, 2)
  }, [lines, bid, ask])

  return (
    <div
      ref={containerRef}
      className="h-[360px] w-full touch-none select-none"
      role="img"
      aria-label="Price chart with the order's entry, stop, and take profit lines. Use the price fields to set them without dragging."
    />
  )
}
