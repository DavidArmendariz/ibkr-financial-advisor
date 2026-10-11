export function fmtGex(n: number | null | undefined, signed = true): string {
  if (typeof n !== 'number') return '—'
  const s = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Math.abs(n))
  if (!signed || n === 0) return s
  return `${n > 0 ? '+' : '−'}${s}`
}

export const fmtStrike = (n: number | null | undefined) =>
  typeof n === 'number' ? n.toFixed(n % 1 === 0 ? 0 : 1) : '—'

export const fmtInt = (n: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)

export const CALL_COLOR = '#3987e5'
export const PUT_COLOR = '#e66767'
