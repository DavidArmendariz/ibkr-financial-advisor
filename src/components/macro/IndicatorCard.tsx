import { AlertTriangle, Clock, Landmark, Moon, Radio, WifiOff } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn, pnlClass } from '@/lib/utils'
import { Sparkline } from './Sparkline'
import { fmtChange, fmtContractMonth, fmtDay, fmtTime, fmtUpdated, fmtValue } from './format'
import type { MacroFreshness, MacroIndicator } from '@/types'

const FRESHNESS: Record<MacroFreshness, { label: string; icon: React.ElementType; className: string }> = {
  live: { label: 'Live', icon: Radio, className: 'text-emerald-400' },
  delayed: { label: 'Delayed', icon: Clock, className: 'text-amber-400' },
  closed: { label: 'Closed', icon: Moon, className: 'text-muted-foreground' },
  daily: { label: 'Official TRM', icon: Landmark, className: 'text-foreground' },
}

export function IndicatorCard({ ind, stale }: { ind: MacroIndicator; stale: boolean }) {
  const fresh = stale
    ? { label: 'Stale', icon: WifiOff, className: 'text-muted-foreground' }
    : FRESHNESS[ind.freshness]
  const change = fmtChange(ind)
  const direction = ind.change_mode === 'bp' ? (ind.change_bp ?? 0) : (ind.change ?? 0)
  const format = (v: number) => fmtValue(ind, v)
  const daily = ind.freshness === 'daily'
  const loading = ind.value === null && !ind.error && !stale
  // Daily points sit at midnight Bogotá; a calendar day reads better than a time.
  const formatTime = daily
    ? (t: number) => new Date(t * 1000).toLocaleDateString('en-US', { timeZone: 'America/Bogota', month: 'short', day: 'numeric' })
    : (t: number) => `${fmtTime(t)} ET`

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{ind.label}</span>
          {ind.contract && ind.contract !== ind.label && (
            <span className="text-xs text-muted-foreground">
              {ind.contract_month ? `${fmtContractMonth(ind.contract_month)} · ` : ''}
              {ind.contract}
            </span>
          )}
        </div>

        <div className={cn('flex flex-col gap-0.5', stale && 'opacity-60')}>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold">{ind.value === null ? '—' : format(ind.value)}</span>
            {ind.unit !== '%' && ind.value !== null && <span className="text-xs text-muted-foreground">{ind.unit}</span>}
          </div>
          <span className="text-sm">
            {change ? <span className={cn('tabular-nums', pnlClass(direction))}>{change}</span> : <span className="text-muted-foreground">{loading ? 'Loading…' : 'No change data'}</span>}
            {ind.previous_close !== null && (
              <span className="text-muted-foreground"> vs {format(ind.previous_close)} prev. close</span>
            )}
          </span>
        </div>

        <Sparkline points={ind.sparkline} previousClose={ind.previous_close} format={format} formatTime={formatTime} label={ind.label} emptyText={loading ? '' : 'No history yet'} />

        <div className="flex items-center gap-1.5 text-xs">
          <fresh.icon className={cn('h-3.5 w-3.5 shrink-0', fresh.className)} />
          <span className={fresh.className}>{fresh.label}</span>
          {ind.updated_at && <span className="text-muted-foreground">· updated {fmtUpdated(ind.updated_at)} ET</span>}
          {ind.valid_from && ind.valid_to && (
            <span className="text-muted-foreground">
              · valid {ind.valid_from === ind.valid_to ? fmtDay(ind.valid_from) : `${fmtDay(ind.valid_from)} – ${fmtDay(ind.valid_to)}`}
            </span>
          )}
        </div>

        {ind.error && (
          <p className="flex items-start gap-1.5 text-xs text-red-400">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{ind.error}</span>
          </p>
        )}
      </CardContent>
    </Card>
  )
}
