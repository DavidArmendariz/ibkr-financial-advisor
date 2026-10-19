import { useState } from 'react'

const LINE = '#3987e5'
const W = 300
const H = 64
const PAD = 4

interface Props {
  points: { time: number; value: number }[]
  previousClose: number | null
  format: (value: number) => string
  formatTime: (unixSeconds: number) => string
  label: string
  emptyText: string
}

// Drawn in a stretched viewBox so it follows the card's width without measuring;
// the end dot and hover marks are HTML so they don't stretch with it.
export function Sparkline({ points, previousClose, format, formatTime, label, emptyText }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  if (points.length < 2) {
    return <div className="flex h-16 items-center text-xs text-muted-foreground">{emptyText}</div>
  }

  const values = points.map((p) => p.value)
  if (previousClose !== null) values.push(previousClose)
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const span = hi - lo || 1
  const x = (i: number) => (i / (points.length - 1)) * W
  const y = (v: number) => PAD + (1 - (v - lo) / span) * (H - 2 * PAD)
  const pct = (i: number, v: number) => ({ left: `${(x(i) / W) * 100}%`, top: `${(y(v) / H) * 100}%` })
  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join('')
  const last = points.length - 1
  const shown = hover ?? last

  const pick = (clientX: number, rect: DOMRect) => {
    const i = Math.round(((clientX - rect.left) / rect.width) * last)
    setHover(Math.max(0, Math.min(last, i)))
  }

  return (
    <div
      className="relative h-16 w-full cursor-crosshair outline-none focus-visible:ring-1 focus-visible:ring-ring"
      tabIndex={0}
      role="img"
      aria-label={`${label} over the period shown, from ${format(points[0].value)} to ${format(points[last].value)}`}
      onPointerMove={(e) => pick(e.clientX, e.currentTarget.getBoundingClientRect())}
      onPointerLeave={() => setHover(null)}
      onBlur={() => setHover(null)}
      onKeyDown={(e) => {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
        e.preventDefault()
        const step = e.key === 'ArrowLeft' ? -1 : 1
        setHover(Math.max(0, Math.min(last, (hover ?? last) + step)))
      }}
    >
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full overflow-visible">
        {previousClose !== null && (
          <line
            x1={0}
            x2={W}
            y1={y(previousClose)}
            y2={y(previousClose)}
            className="stroke-muted-foreground/50"
            strokeWidth={1}
            strokeDasharray="3 3"
            vectorEffect="non-scaling-stroke"
          />
        )}
        <path d={path} fill="none" stroke={LINE} strokeWidth={2} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        {hover !== null && (
          <line x1={x(hover)} x2={x(hover)} y1={0} y2={H} className="stroke-muted-foreground" strokeWidth={1} vectorEffect="non-scaling-stroke" />
        )}
      </svg>
      <span
        className="pointer-events-none absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
        style={{ ...pct(shown, points[shown].value), background: LINE }}
      />
      {hover !== null && (
        <div
          className="pointer-events-none absolute top-full z-10 mt-1 -translate-x-1/2 whitespace-nowrap rounded border border-border bg-popover px-1.5 py-0.5 text-xs text-popover-foreground shadow"
          style={{ left: `${Math.min(85, Math.max(15, (x(hover) / W) * 100))}%` }}
        >
          <span className="text-muted-foreground">{formatTime(points[hover].time)}</span> {format(points[hover].value)}
        </div>
      )}
    </div>
  )
}
