import { Fragment } from 'react'
import { ErrorRow } from '@/components/macro/parts'
import { cn } from '@/lib/utils'
import { HIGHLIGHT, HIGHLIGHT_COLOR, QUADRANTS, QUADRANT_TINT, periodLabel, reading } from './format'
import type { RotationEtf, RotationTimeframe } from '@/types'

const HEADERS: { label: string; numeric?: boolean }[] = [
  { label: 'ETF' },
  { label: 'Sector' },
  { label: 'RS-Ratio', numeric: true },
  { label: 'RS-Momentum', numeric: true },
  { label: 'In quadrant for', numeric: true },
]

interface Props {
  etfs: RotationEtf[]
  timeframe: RotationTimeframe
  active: string | null
  selected: string | null
  onSelect: (symbol: string | null) => void
  onHover: (symbol: string | null) => void
}

export function RotationTable({ etfs, timeframe, active, selected, onSelect, onHover }: Props) {
  const current = (e: RotationEtf) => e[timeframe].points.at(-1)
  const groups = QUADRANTS.map((q) => ({
    name: q as string,
    rows: etfs.filter((e) => current(e)?.quadrant === q),
  }))
  const missing = etfs.filter((e) => !current(e))
  if (missing.length) groups.push({ name: 'No readings', rows: missing })

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-muted-foreground">
            {HEADERS.map((h) => (
              <th key={h.label} scope="col" className={cn('whitespace-nowrap px-3 py-2 font-medium', h.numeric ? 'text-right' : 'text-left')}>
                {h.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups
            .filter((g) => g.rows.length > 0)
            .map((g) => (
              <Fragment key={g.name}>
                <tr className="border-b border-border bg-muted/40">
                  <th
                    colSpan={HEADERS.length}
                    scope="colgroup"
                    className="px-3 py-1.5 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground"
                  >
                    <span className="inline-flex items-center gap-2">
                      {g.name in QUADRANT_TINT && (
                        <span
                          className="h-2.5 w-2.5 rounded-sm"
                          style={{
                            background: QUADRANT_TINT[g.name as keyof typeof QUADRANT_TINT],
                          }}
                        />
                      )}
                      {g.name}
                    </span>
                  </th>
                </tr>
                {g.rows.map((e) => {
                  const p = current(e)
                  const isSelected = selected === e.symbol
                  return (
                    <Fragment key={e.symbol}>
                      <tr
                        className={cn(
                          'cursor-pointer border-border transition-colors hover:bg-accent/40',
                          !e.error && 'border-b',
                          active === e.symbol && 'bg-accent/40',
                        )}
                        onClick={() => onSelect(isSelected ? null : e.symbol)}
                        onPointerEnter={() => onHover(e.symbol)}
                        onPointerLeave={() => onHover(null)}
                      >
                        <td className="whitespace-nowrap px-3 py-2 font-medium">
                          <button
                            type="button"
                            aria-pressed={isSelected}
                            aria-label={`Highlight ${e.symbol} on the graph`}
                            className="inline-flex items-center gap-2 outline-none focus-visible:underline"
                            onClick={(ev) => {
                              ev.stopPropagation()
                              onSelect(isSelected ? null : e.symbol)
                            }}
                          >
                            <span
                              className="h-2 w-2 rounded-full"
                              style={{
                                background: e.symbol === HIGHLIGHT ? HIGHLIGHT_COLOR : 'var(--muted-foreground)',
                              }}
                            />
                            {e.symbol}
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{e.name}</td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{p ? reading(p.ratio) : '—'}</td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{p ? reading(p.momentum) : '—'}</td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted-foreground">
                          {p ? periodLabel(e[timeframe].periods, timeframe) : '—'}
                        </td>
                      </tr>
                      {e.error && (
                        <tr className="border-b border-border">
                          <td colSpan={HEADERS.length} className="px-3 pb-2">
                            <ErrorRow error={e.error} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </Fragment>
            ))}
        </tbody>
      </table>
    </div>
  )
}
