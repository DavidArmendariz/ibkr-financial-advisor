export const multiple = (v: number | null) => (v === null ? '—' : `${v >= 100 ? v.toFixed(0) : v.toFixed(1)}×`)

export const percent = (v: number | null, digits = 1) => (v === null ? '—' : `${v.toFixed(digits)}%`)

export const signedPercent = (v: number | null) => (v === null ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(2)}%`)

// Finnhub reports market cap in millions.
export function marketCap(millions: number | null) {
  if (millions === null) return '—'
  if (millions >= 1_000_000) return `$${(millions / 1_000_000).toFixed(2)}T`
  if (millions >= 1_000) return `$${(millions / 1_000).toFixed(1)}B`
  return `$${millions.toFixed(0)}M`
}

// How far the stock's multiple sits from a median, as a percent of the median.
export function versus(value: number | null, median: number | null) {
  if (value === null || median === null) return null
  return (value / median - 1) * 100
}

export const newsTime = (unixSeconds: number) =>
  new Date(unixSeconds * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
