import { useEffect, useRef, useState } from 'react'
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { getChartData } from '@/lib/api'

export const DURATIONS = [
  { label: '1D', duration: '1 D', barSize: '5 mins' },
  { label: '5D', duration: '5 D', barSize: '30 mins' },
  { label: '1M', duration: '1 M', barSize: '1 day' },
  { label: '3M', duration: '3 M', barSize: '1 day' },
  { label: '1Y', duration: '1 Y', barSize: '1 day' },
]

interface Props {
  symbol: string | null
  initialPeriod?: string
  height?: number
}

export function TradingChart({ symbol, initialPeriod, height = 320 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const [activeDuration, setActiveDuration] = useState(
    () => DURATIONS.find((d) => d.label === initialPeriod) ?? DURATIONS[0],
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Create chart on mount
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'rgba(255,255,255,0.5)',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderColor: 'rgba(255,255,255,0.06)', timeVisible: true },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.06)' },
      width: containerRef.current.clientWidth,
      height,
    })

    seriesRef.current = chart.addCandlestickSeries({
      upColor: '#34d399',
      downColor: '#f87171',
      borderVisible: false,
      wickUpColor: '#34d399',
      wickDownColor: '#f87171',
    })

    chartRef.current = chart

    const ro = new ResizeObserver((entries) => {
      if (entries[0]) chart.applyOptions({ width: entries[0].contentRect.width })
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [])

  // Fetch data when symbol or duration changes
  useEffect(() => {
    if (!symbol || !seriesRef.current) return

    setLoading(true)
    setError(null)

    getChartData(symbol, activeDuration.duration, activeDuration.barSize)
      .then((bars) => {
        const data: CandlestickData<Time>[] = bars.map((b) => ({
          time: b.time as Time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        }))
        seriesRef.current?.setData(data)
        chartRef.current?.timeScale().fitContent()
      })
      .catch(() => setError('Failed to load chart data'))
      .finally(() => setLoading(false))
  }, [symbol, activeDuration])

  return (
    <Card className="flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm">
          {symbol ? `${symbol} — ${activeDuration.label}` : 'Select a position to chart'}
        </CardTitle>
        <div className="flex gap-1">
          {DURATIONS.map((d) => (
            <Button
              key={d.label}
              variant={activeDuration.label === d.label ? 'secondary' : 'ghost'}
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={() => setActiveDuration(d)}
            >
              {d.label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="p-0 pb-2 px-4">
        {error && (
          <div className="flex h-32 items-center justify-center text-xs text-destructive">
            {error}
          </div>
        )}
        {!symbol && (
          <div className="flex h-32 items-center justify-center text-xs text-muted-foreground">
            Click a row in the positions table to load the chart
          </div>
        )}
        <div
          ref={containerRef}
          className="w-full"
          style={{ opacity: loading ? 0.5 : 1, transition: 'opacity 0.2s' }}
        />
      </CardContent>
    </Card>
  )
}
