// Values arrive in billions of dollars.
export const LEVEL_COLOR = '#3987e5'
export const GROWTH_COLOR = '#3987e5'
export const CONTRACTION_COLOR = '#e66767'

export function fmtDollars(billions: number, signed = false) {
  const sign = signed ? (billions > 0 ? '+' : billions < 0 ? '−' : '') : billions < 0 ? '−' : ''
  const abs = Math.abs(billions)
  return abs >= 1000 ? `${sign}$${(abs / 1000).toFixed(2)}T` : `${sign}$${abs.toFixed(1)}B`
}

export function fmtPct(value: number, digits = 2) {
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return `${sign}${Math.abs(value).toFixed(digits)}%`
}

export function fmtMonth(month: string, style: 'long' | 'short' = 'long') {
  return new Date(`${month}T12:00:00`).toLocaleDateString('en-US', { month: style, year: 'numeric' })
}

export function fmtDay(day: string) {
  return new Date(`${day.slice(0, 10)}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
