import type { RotationQuadrant, RotationTimeframe } from '@/types'

export const QUADRANTS: RotationQuadrant[] = ['Leading', 'Weakening', 'Lagging', 'Improving']

// Faint tints behind the quadrant names; the names carry the meaning.
export const QUADRANT_TINT: Record<RotationQuadrant, string> = {
  Leading: '#199e70',
  Weakening: '#c98500',
  Lagging: '#d95926',
  Improving: '#8b6fd6',
}

export const HIGHLIGHT = 'SMH'
export const HIGHLIGHT_COLOR = '#3987e5'

export const reading = (n: number) => n.toFixed(2)

// Bar times are midnight UTC of the session date.
export const sessionDate = (t: number) =>
  new Date(t * 1000).toLocaleDateString(undefined, {
    timeZone: 'UTC',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

export const periodLabel = (n: number, timeframe: RotationTimeframe) =>
  `${n} ${timeframe === 'weekly' ? (n === 1 ? 'week' : 'weeks') : n === 1 ? 'day' : 'days'}`
