import type { MoneySupplyRange } from '@/types'

const YEARS: Record<Exclude<MoneySupplyRange, 'all'>, number> = { '5y': 5, '10y': 10, '25y': 25 }

// First month shown: the newest month minus the range, so "5Y" is the last 61 months
// and both ends of the period land on the same calendar month.
export function calcCutoff(latest: string | undefined, range: MoneySupplyRange): string | null {
  if (!latest || range === 'all') return null
  return `${Number(latest.slice(0, 4)) - YEARS[range]}${latest.slice(4)}`
}
