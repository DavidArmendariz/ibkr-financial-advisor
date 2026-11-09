import { ArrowDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { multiple, versus } from './format'
import type { FundamentalsMultiple } from '@/types'

function Value({ m }: { m: FundamentalsMultiple }) {
  if (m.status === 'not_meaningful') return <span className="text-muted-foreground">Not meaningful</span>
  return <>{multiple(m.value)}</>
}

// The marker is spelled out, so it never depends on colour alone.
function Comparison({ value, median, cheaper, missing }: { value: number | null; median: number | null; cheaper: boolean | null; missing: string }) {
  if (median === null) return <span className="text-xs text-muted-foreground">{missing}</span>
  const diff = versus(value, median)
  return (
    <div className="flex flex-col items-end gap-0.5">
      <span className="tabular-nums">{multiple(median)}</span>
      {diff !== null && (
        <span className={cn('inline-flex items-center gap-1 text-xs tabular-nums', cheaper ? 'text-emerald-400' : 'text-muted-foreground')}>
          {cheaper && <ArrowDown className="h-3 w-3" aria-hidden />}
          {Math.abs(diff).toFixed(0)}% {diff < 0 ? 'below' : 'above'}
          {cheaper ? ' · cheaper' : ''}
        </span>
      )}
    </div>
  )
}

export function ValuationTable({ multiples }: { multiples: FundamentalsMultiple[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-muted-foreground">
            <th scope="col" className="px-3 py-2 text-left font-medium">Multiple</th>
            <th scope="col" className="px-3 py-2 text-right font-medium">Trailing</th>
            <th scope="col" className="px-3 py-2 text-right font-medium">Peer median</th>
            <th scope="col" className="px-3 py-2 text-right font-medium">5 fiscal-year median</th>
          </tr>
        </thead>
        <tbody>
          {multiples.map((m) => (
            <tr key={m.key} className="border-b border-border last:border-0 align-top">
              <th scope="row" className="whitespace-nowrap px-3 py-2 text-left font-medium">{m.label}</th>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                <Value m={m} />
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                <Comparison value={m.value} median={m.peer_median} cheaper={m.cheaper_than_peers} missing="Not enough peers" />
                {m.peer_median !== null && <span className="block text-right text-xs text-muted-foreground">{m.peer_count} peers</span>}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                <Comparison
                  value={m.value}
                  median={m.history_median}
                  cheaper={m.cheaper_than_history}
                  missing={m.has_history ? 'Not enough history' : 'No yearly history'}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
