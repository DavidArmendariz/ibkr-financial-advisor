import { DURATIONS, TradingChart } from '@/components/dashboard/TradingChart'

interface PriceChartSpec {
  symbol: string
  period?: string
}

// Model output: accept only a plausible ticker and a known period.
export function parsePriceChartSpec(source: string): PriceChartSpec | null {
  let raw: unknown
  try {
    raw = JSON.parse(source)
  } catch {
    return null
  }
  if (!raw || typeof raw !== 'object') return null
  const { symbol, period } = raw as Record<string, unknown>
  if (typeof symbol !== 'string' || !/^[A-Za-z][A-Za-z0-9.]{0,9}$/.test(symbol)) return null
  const knownPeriod = typeof period === 'string' && DURATIONS.some((d) => d.label === period)
  return { symbol: symbol.toUpperCase(), period: knownPeriod ? period : '3M' }
}

export function PriceChartBlock({ symbol, period }: PriceChartSpec) {
  return (
    <div className="my-3 w-[560px] max-w-full">
      <TradingChart symbol={symbol} initialPeriod={period} height={240} />
    </div>
  )
}
