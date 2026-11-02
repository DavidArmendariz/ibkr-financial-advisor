import { Moon, Radio, WifiOff } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Sparkline } from '@/components/macro/Sparkline'
import { fmtDelay } from '@/components/macro/format'
import { ErrorRow } from '@/components/macro/parts'
import { cn, pnlClass } from '@/lib/utils'
import type { GlobalInstrument } from '@/types'

export function fmtNumber(value: number, decimals: number) {
  return value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export function changeSign(value: number) {
  return value > 0 ? '+' : value < 0 ? '−' : ''
}

function fmtChange(m: GlobalInstrument) {
  if (m.change === null || m.change_pct === null) return null
  const sign = changeSign(m.change)
  return `${sign}${fmtNumber(Math.abs(m.change), m.decimals)} (${sign}${Math.abs(m.change_pct).toFixed(2)}%)`
}

export function fmtLocal(seconds: number, tz: string, withDay: boolean) {
  return new Date(seconds * 1000).toLocaleString('en-US', {
    timeZone: tz,
    ...(withDay ? { weekday: 'short' as const } : {}),
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function MarketCard({ market: m, stale }: { market: GlobalInstrument; stale: boolean }) {
  const change = fmtChange(m)
  const loading = m.value === null && !m.error && !stale
  const status = stale
    ? { label: 'Stale', icon: WifiOff, className: 'text-muted-foreground' }
    : m.market_open
      ? { label: 'Open', icon: Radio, className: 'text-emerald-400' }
      : { label: 'Closed', icon: Moon, className: 'text-muted-foreground' }

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{m.label}</span>

        <div className={cn('flex flex-col gap-0.5', stale && 'opacity-60')}>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold">{m.value === null ? '—' : fmtNumber(m.value, m.decimals)}</span>
            {m.value !== null && <span className="text-xs text-muted-foreground">{m.unit}</span>}
          </div>
          <span className="text-sm">
            {change ? (
              <span className={cn('tabular-nums', pnlClass(m.change ?? 0))}>{change}</span>
            ) : (
              <span className="text-muted-foreground">{loading ? 'Loading…' : 'No change data'}</span>
            )}
            {m.previous_close !== null && <span className="text-muted-foreground"> vs {fmtNumber(m.previous_close, m.decimals)} prev. close</span>}
          </span>
        </div>

        <Sparkline
          points={m.sparkline}
          previousClose={m.previous_close}
          format={(v) => fmtNumber(v, m.decimals)}
          formatTime={(t) => `${fmtLocal(t, m.tz, false)} ${m.place}`}
          label={m.label}
          emptyText={loading ? '' : 'No intraday data'}
        />

        <div className="flex flex-wrap items-center gap-x-1.5 text-xs">
          <status.icon className={cn('h-3.5 w-3.5 shrink-0', status.className)} />
          <span className={status.className}>{status.label}</span>
          {m.data_time !== null && (
            <span className="text-muted-foreground">
              · data from {fmtLocal(m.data_time, m.tz, true)} {m.place}
            </span>
          )}
          {!stale && m.delay_minutes !== null && <span className="text-muted-foreground">· {fmtDelay(m.delay_minutes)}</span>}
        </div>
        <ErrorRow error={m.error} />
      </CardContent>
    </Card>
  )
}
