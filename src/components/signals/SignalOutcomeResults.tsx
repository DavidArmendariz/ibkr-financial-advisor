import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import * as api from '@/lib/api'
import { cn, pnlClass } from '@/lib/utils'
import type { OutcomeHorizon, OutcomeStats, SignalOutcomeResults } from '@/types'

const POLL_MS = 60_000
const HORIZONS: { key: OutcomeHorizon; label: string }[] = [
  { key: '5m', label: '5 min' },
  { key: '15m', label: '15 min' },
  { key: '30m', label: '30 min' },
]

function fmtMove(value: number | null) {
  if (value === null) return '—'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function Move({ value, muted }: { value: number | null; muted: boolean }) {
  return <td className={cn('px-3 py-2 text-right tabular-nums', muted ? 'text-muted-foreground' : value !== null && pnlClass(value))}>{fmtMove(value)}</td>
}

function Row({ name, stats, horizon, baseline }: { name: string; stats: OutcomeStats; horizon: OutcomeHorizon; baseline?: boolean }) {
  const h = stats.horizons[horizon]
  const muted = h.small_sample && !baseline
  return (
    <tr className={cn('border-b border-border last:border-0', baseline && 'bg-accent/30')}>
      <td className="whitespace-nowrap px-3 py-2 font-medium">
        {name}
        {muted && h.count > 0 && <span className="ml-2 rounded border border-border px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">Small sample</span>}
      </td>
      <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">{h.count.toLocaleString('en-US')}</td>
      <Move value={h.average} muted={muted} />
      <Move value={h.median} muted={muted} />
      <td className={cn('px-3 py-2 text-right tabular-nums', muted && 'text-muted-foreground')}>{h.up_share === null ? '—' : `${Math.round(h.up_share * 100)}%`}</td>
      <Move value={stats.average_max_up} muted={muted} />
      <Move value={stats.average_max_down} muted={muted} />
    </tr>
  )
}

export function SignalOutcomeResultsTable() {
  const [results, setResults] = useState<SignalOutcomeResults | null>(null)
  const [horizon, setHorizon] = useState<OutcomeHorizon>('15m')

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const next = await api.getSignalOutcomes()
        if (alive) setResults(next)
      } catch {
        // The signal list below already reports an unreachable backend.
      }
      if (alive) timer = setTimeout(load, POLL_MS)
    }
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  if (!results) return null
  const empty = results.triggers.length === 0

  return (
    <section className="rounded-lg border border-border" aria-label="Results by trigger">
      <div className="flex flex-wrap items-start justify-between gap-3 p-4">
        <div>
          <h2 className="text-sm font-medium">Results by trigger</h2>
          <p className="text-xs text-muted-foreground">
            How SOXL moved after past signals, before costs. This describes the past and doesn't predict future signals.
          </p>
          {results.pending > 0 && (
            <p className="mt-1 text-xs text-muted-foreground">
              {results.pending.toLocaleString('en-US')} {results.pending === 1 ? 'signal' : 'signals'} waiting to be measured
            </p>
          )}
        </div>
        {!empty && (
          <div className="no-drag flex gap-1" role="group" aria-label="Time after the signal">
            {HORIZONS.map((h) => (
              <Button key={h.key} size="sm" variant={horizon === h.key ? 'default' : 'outline'} aria-pressed={horizon === h.key} onClick={() => setHorizon(h.key)}>
                {h.label}
              </Button>
            ))}
          </div>
        )}
      </div>
      {empty ? (
        <p className="border-t border-border p-4 text-center text-sm text-muted-foreground">No signals measured yet</p>
      ) : (
        <div className="overflow-x-auto border-t border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th scope="col" className="px-3 py-2 text-left font-medium">Trigger</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Signals</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Average</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Median</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Up</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Avg largest up</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">Avg largest down</th>
              </tr>
            </thead>
            <tbody>
              {results.baseline && <Row name="Baseline: every minute" stats={results.baseline} horizon={horizon} baseline />}
              {results.triggers.map((t) => (
                <Row key={t.signal_type} name={t.signal_type.replace(/_/g, ' ')} stats={t} horizon={horizon} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!empty && (
        <p className="border-t border-border p-3 text-[11px] text-muted-foreground">
          Largest moves cover the 30 minutes after each signal. Under {results.min_sample} signals is too few to rely on.
          {results.baseline_days > 0 && ` Baseline covers ${results.baseline_days} ${results.baseline_days === 1 ? 'day' : 'days'}.`}
        </p>
      )}
    </section>
  )
}
