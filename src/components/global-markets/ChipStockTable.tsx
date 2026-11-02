import { Fragment } from 'react'
import { Moon, Radio, WifiOff } from 'lucide-react'
import { fmtDelay } from '@/components/macro/format'
import { ErrorRow } from '@/components/macro/parts'
import { cn, pnlClass } from '@/lib/utils'
import { changeSign, fmtLocal, fmtNumber } from './MarketCard'
import type { GlobalInstrument } from '@/types'

const HEADERS: { label: string; numeric?: boolean }[] = [
  { label: 'Market' },
  { label: 'Company' },
  { label: 'Last', numeric: true },
  { label: 'Change', numeric: true },
  { label: 'Change %', numeric: true },
  { label: 'Prev. close', numeric: true },
  { label: 'Status' },
  { label: 'Data from' },
  { label: 'Delay' },
]

function Status({ open, stale }: { open: boolean; stale: boolean }) {
  const s = stale
    ? { label: 'Stale', icon: WifiOff, className: 'text-muted-foreground' }
    : open
      ? { label: 'Open', icon: Radio, className: 'text-emerald-400' }
      : { label: 'Closed', icon: Moon, className: 'text-muted-foreground' }
  return (
    <span className={cn('inline-flex items-center gap-1.5', s.className)}>
      <s.icon className="h-3.5 w-3.5 shrink-0" />
      {s.label}
    </span>
  )
}

export function ChipStockTable({ stocks, stale }: { stocks: GlobalInstrument[]; stale: (m: GlobalInstrument) => boolean }) {
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
          {stocks.map((m, i) => {
            const isStale = stale(m)
            const firstInMarket = i === 0 || stocks[i - 1].group !== m.group
            const moved = cn('px-3 py-2 text-right tabular-nums whitespace-nowrap', m.change === null ? 'text-muted-foreground' : pnlClass(m.change))
            return (
              <Fragment key={m.key}>
                <tr className={cn('border-border', !m.error && 'border-b last:border-0', isStale && 'opacity-60')}>
                  <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{firstInMarket ? m.group : ''}</td>
                  <td className="whitespace-nowrap px-3 py-2 font-medium">{m.label}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                    {m.value === null ? '—' : fmtNumber(m.value, m.decimals)} <span className="text-xs text-muted-foreground">{m.currency}</span>
                  </td>
                  <td className={moved}>{m.change === null ? '—' : `${changeSign(m.change)}${fmtNumber(Math.abs(m.change), m.decimals)}`}</td>
                  <td className={moved}>{m.change_pct === null ? '—' : `${changeSign(m.change_pct)}${Math.abs(m.change_pct).toFixed(2)}%`}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted-foreground">
                    {m.previous_close === null ? '—' : fmtNumber(m.previous_close, m.decimals)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-xs">
                    <Status open={m.market_open} stale={isStale} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-xs text-muted-foreground">
                    {m.data_time === null ? '—' : `${fmtLocal(m.data_time, m.tz, true)} ${m.place}`}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-xs text-muted-foreground">
                    {m.delay_minutes === null || isStale ? '—' : fmtDelay(m.delay_minutes)}
                  </td>
                </tr>
                {m.error && (
                  <tr className="border-b border-border last:border-0">
                    <td colSpan={HEADERS.length} className="px-3 pb-2">
                      <ErrorRow error={m.error} />
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
