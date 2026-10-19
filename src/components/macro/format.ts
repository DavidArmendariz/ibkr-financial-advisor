import type { MacroIndicator } from '@/types'

export function fmtValue(ind: MacroIndicator, value: number) {
  const n = value.toLocaleString('en-US', { minimumFractionDigits: ind.decimals, maximumFractionDigits: ind.decimals })
  return ind.unit === '%' ? `${n}%` : n
}

export function fmtChange(ind: MacroIndicator) {
  if (ind.change === null) return null
  const sign = (v: number) => (v > 0 ? '+' : v < 0 ? '−' : '')
  if (ind.change_mode === 'bp' && ind.change_bp !== null) {
    const bp = Math.round(ind.change_bp)
    return `${sign(bp)}${Math.abs(bp)} bp`
  }
  const abs = Math.abs(ind.change).toLocaleString('en-US', { minimumFractionDigits: ind.decimals, maximumFractionDigits: ind.decimals })
  const pct = ind.change_pct === null ? '' : ` (${sign(ind.change_pct)}${Math.abs(ind.change_pct).toFixed(2)}%)`
  return `${sign(ind.change)}${abs}${pct}`
}

export function fmtContractMonth(yyyymm: string) {
  const d = new Date(Number(yyyymm.slice(0, 4)), Number(yyyymm.slice(4, 6)) - 1, 1)
  return d.toLocaleString('en-US', { month: 'short', year: 'numeric' })
}

export function fmtTime(unixSeconds: number) {
  return new Date(unixSeconds * 1000).toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function fmtDay(isoDate: string) {
  // Plain calendar dates; parse as local noon so no time zone shifts the day.
  return new Date(`${isoDate.slice(0, 10)}T12:00:00`).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export function fmtUpdated(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
