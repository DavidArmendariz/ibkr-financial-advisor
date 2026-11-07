import { useState } from 'react'
import { HIGHLIGHT, HIGHLIGHT_COLOR, QUADRANT_TINT, reading, sessionDate } from './format'
import type { RotationEtf, RotationPoint, RotationQuadrant, RotationTimeframe } from '@/types'

const W = 720
const H = 540
const M = { left: 52, right: 20, top: 16, bottom: 44 }
const PLOT_W = W - M.left - M.right
const PLOT_H = H - M.top - M.bottom
const LABEL_W = 40
const LABEL_H = 13

interface Trail {
  etf: RotationEtf
  points: RotationPoint[]
}

interface Props {
  etfs: RotationEtf[]
  timeframe: RotationTimeframe
  tail: number
  active: string | null
  onHover: (symbol: string | null) => void
}

function niceStep(span: number) {
  const raw = span / 4
  return [0.25, 0.5, 1, 2, 5, 10].find((s) => s >= raw) ?? 10
}

function ticks(half: number) {
  const step = niceStep(half * 2)
  const out: number[] = []
  for (let v = Math.ceil((100 - half) / step) * step; v <= 100 + half + 1e-9; v += step) out.push(Number(v.toFixed(4)))
  return out
}

// Labels sit right of their head and are pushed down past any label they'd collide with.
function placeLabels(heads: { symbol: string; x: number; y: number }[]) {
  const placed: {
    symbol: string
    x: number
    y: number
    anchor: 'start' | 'end'
  }[] = []
  for (const h of [...heads].sort((a, b) => a.y - b.y)) {
    const right = h.x + 8 + LABEL_W <= W - M.right
    const x = right ? h.x + 8 : h.x - 8
    const left = right ? x : x - LABEL_W
    let y = h.y + 4
    for (let moved = true; moved;) {
      moved = false
      for (const p of placed) {
        const pLeft = p.anchor === 'start' ? p.x : p.x - LABEL_W
        if (Math.abs(pLeft - left) < LABEL_W && Math.abs(p.y - y) < LABEL_H) {
          y = p.y + LABEL_H
          moved = true
        }
      }
    }
    placed.push({ symbol: h.symbol, x, y, anchor: right ? 'start' : 'end' })
  }
  return new Map(placed.map((p) => [p.symbol, p]))
}

export function RotationGraph({ etfs, timeframe, tail, active, onHover }: Props) {
  const [hover, setHover] = useState<{ symbol: string; index: number } | null>(null)
  const trails: Trail[] = etfs.map((etf) => ({ etf, points: etf[timeframe].points.slice(-tail) })).filter((t) => t.points.length > 0)

  if (trails.length === 0) {
    return <div className="flex aspect-[4/3] w-full items-center justify-center text-sm text-muted-foreground">No readings yet.</div>
  }

  const all = trails.flatMap((t) => t.points)
  // Symmetric around 100 on each axis, so the quadrants always meet in the middle.
  const half = (key: 'ratio' | 'momentum') => Math.max(1.5, ...all.map((p) => Math.abs(p[key] - 100))) * 1.1
  const hx = half('ratio')
  const hy = half('momentum')
  const x = (v: number) => M.left + ((v - (100 - hx)) / (2 * hx)) * PLOT_W
  const y = (v: number) => M.top + (1 - (v - (100 - hy)) / (2 * hy)) * PLOT_H
  const cx = x(100)
  const cy = y(100)

  const focus = hover?.symbol ?? active
  const order = [...trails].sort((a, b) => rank(a.etf.symbol) - rank(b.etf.symbol))
  function rank(symbol: string) {
    return symbol === focus ? 2 : symbol === HIGHLIGHT ? 1 : 0
  }
  const labels = placeLabels(
    trails.map((t) => ({
      symbol: t.etf.symbol,
      x: x(t.points.at(-1)!.ratio),
      y: y(t.points.at(-1)!.momentum),
    })),
  )

  const quadrants: {
    name: RotationQuadrant
    x: number
    y: number
    w: number
    h: number
    tx: number
    ty: number
    anchor: 'start' | 'end'
  }[] = [
    {
      name: 'Improving',
      x: M.left,
      y: M.top,
      w: cx - M.left,
      h: cy - M.top,
      tx: M.left + 8,
      ty: M.top + 16,
      anchor: 'start',
    },
    {
      name: 'Leading',
      x: cx,
      y: M.top,
      w: W - M.right - cx,
      h: cy - M.top,
      tx: W - M.right - 8,
      ty: M.top + 16,
      anchor: 'end',
    },
    {
      name: 'Lagging',
      x: M.left,
      y: cy,
      w: cx - M.left,
      h: H - M.bottom - cy,
      tx: M.left + 8,
      ty: H - M.bottom - 8,
      anchor: 'start',
    },
    {
      name: 'Weakening',
      x: cx,
      y: cy,
      w: W - M.right - cx,
      h: H - M.bottom - cy,
      tx: W - M.right - 8,
      ty: H - M.bottom - 8,
      anchor: 'end',
    },
  ]

  const hovered = hover && trails.find((t) => t.etf.symbol === hover.symbol)
  const hoveredPoint = hovered ? hovered.points[hover.index] : null

  const styleFor = (symbol: string) => {
    if (symbol === focus) return { stroke: 'var(--foreground)', width: 2, opacity: 1 }
    if (symbol === HIGHLIGHT) return { stroke: HIGHLIGHT_COLOR, width: 2, opacity: focus ? 0.6 : 1 }
    return {
      stroke: 'var(--muted-foreground)',
      width: 1.5,
      opacity: focus ? 0.12 : 0.35,
    }
  }

  return (
    <div className="relative aspect-[4/3] w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="absolute inset-0 h-full w-full"
        role="img"
        aria-label={`Relative rotation graph of ${trails.length} sector ETFs against SPY. The table below lists every reading.`}
        onPointerLeave={() => {
          setHover(null)
          onHover(null)
        }}
      >
        {quadrants.map((q) => (
          <g key={q.name}>
            <rect x={q.x} y={q.y} width={Math.max(0, q.w)} height={Math.max(0, q.h)} fill={QUADRANT_TINT[q.name]} opacity={0.07} />
            <text x={q.tx} y={q.ty} textAnchor={q.anchor} className="fill-muted-foreground text-[13px] font-medium uppercase tracking-wider">
              {q.name}
            </text>
          </g>
        ))}

        {ticks(hx).map((v) => (
          <g key={`x${v}`}>
            <line x1={x(v)} x2={x(v)} y1={M.top} y2={H - M.bottom} stroke="var(--border)" />
            <text x={x(v)} y={H - M.bottom + 16} textAnchor="middle" className="fill-muted-foreground text-[11px] tabular-nums">
              {v}
            </text>
          </g>
        ))}
        {ticks(hy).map((v) => (
          <g key={`y${v}`}>
            <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)} stroke="var(--border)" />
            <text x={M.left - 6} y={y(v) + 4} textAnchor="end" className="fill-muted-foreground text-[11px] tabular-nums">
              {v}
            </text>
          </g>
        ))}
        <line x1={cx} x2={cx} y1={M.top} y2={H - M.bottom} stroke="var(--muted-foreground)" strokeOpacity={0.5} />
        <line x1={M.left} x2={W - M.right} y1={cy} y2={cy} stroke="var(--muted-foreground)" strokeOpacity={0.5} />
        <text x={M.left + PLOT_W / 2} y={H - 6} textAnchor="middle" className="fill-muted-foreground text-[12px]">
          RS-Ratio: strength against SPY →
        </text>
        <text transform={`translate(14 ${M.top + PLOT_H / 2}) rotate(-90)`} textAnchor="middle" className="fill-muted-foreground text-[12px]">
          RS-Momentum: is that strength rising? →
        </text>

        {order.map(({ etf, points }) => {
          const s = styleFor(etf.symbol)
          const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.ratio).toFixed(1)},${y(p.momentum).toFixed(1)}`).join('')
          return (
            <g key={etf.symbol} opacity={s.opacity}>
              <path d={path} fill="none" stroke={s.stroke} strokeWidth={s.width} strokeLinejoin="round" strokeLinecap="round" />
              {points.slice(0, -1).map((p, i) => (
                <circle key={i} cx={x(p.ratio)} cy={y(p.momentum)} r={2.5} fill={s.stroke} />
              ))}
              {points.map((p, i) => (
                <circle
                  key={`hit${i}`}
                  cx={x(p.ratio)}
                  cy={y(p.momentum)}
                  r={9}
                  fill="transparent"
                  className="cursor-pointer"
                  onPointerEnter={() => {
                    setHover({ symbol: etf.symbol, index: i })
                    onHover(etf.symbol)
                  }}
                />
              ))}
            </g>
          )
        })}
        {order.map(({ etf, points }) => {
          const label = labels.get(etf.symbol)!
          const head = points.at(-1)!
          const strong = etf.symbol === focus || (etf.symbol === HIGHLIGHT && !focus)
          const dimmed = focus !== null && etf.symbol !== focus
          return (
            <g key={`head${etf.symbol}`} className="pointer-events-none" opacity={dimmed ? 0.45 : 1}>
              <circle cx={x(head.ratio)} cy={y(head.momentum)} r={5} fill={styleFor(etf.symbol).stroke} stroke="var(--card)" strokeWidth={2} />
              <text
                key={`label${etf.symbol}`}
                x={label.x}
                y={label.y}
                textAnchor={label.anchor}
                className={strong ? 'fill-foreground text-[12px] font-semibold' : 'fill-muted-foreground text-[11px] font-medium'}
              >
                {etf.symbol}
              </text>
            </g>
          )
        })}
      </svg>

      {hovered && hoveredPoint && (
        <div
          className="pointer-events-none absolute z-10 w-max rounded border border-border bg-popover px-2 py-1.5 text-xs text-popover-foreground shadow"
          style={{
            left: `${Math.min(85, Math.max(15, (x(hoveredPoint.ratio) / W) * 100))}%`,
            top: `${(y(hoveredPoint.momentum) / H) * 100}%`,
            transform: `translate(-50%, ${y(hoveredPoint.momentum) > H / 2 ? 'calc(-100% - 12px)' : '12px'})`,
          }}
        >
          <div className="font-medium">
            {hovered.etf.symbol} <span className="font-normal text-muted-foreground">{hovered.etf.name}</span>
          </div>
          <div className="text-muted-foreground">
            {timeframe === 'weekly' ? 'Week to ' : ''}
            {sessionDate(hoveredPoint.time)}
          </div>
          <div className="mt-1 grid grid-cols-[auto_auto] gap-x-3 tabular-nums">
            <span className="text-muted-foreground">RS-Ratio</span>
            <span className="text-right">{reading(hoveredPoint.ratio)}</span>
            <span className="text-muted-foreground">RS-Momentum</span>
            <span className="text-right">{reading(hoveredPoint.momentum)}</span>
            <span className="text-muted-foreground">Quadrant</span>
            <span className="text-right">{hoveredPoint.quadrant}</span>
          </div>
        </div>
      )}
    </div>
  )
}
