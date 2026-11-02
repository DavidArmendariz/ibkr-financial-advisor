import { AlertTriangle, Clock, Landmark, Moon, Radio, WifiOff } from 'lucide-react'
import { cn, pnlClass } from '@/lib/utils'
import { fmtChange, fmtContractMonth, fmtDay, fmtDelay, fmtUpdated, fmtValue } from './format'
import type { MacroFreshness, MacroIndicator } from '@/types'

const FRESHNESS: Record<MacroFreshness, { label: string; icon: React.ElementType; className: string }> = {
  live: { label: 'Live', icon: Radio, className: 'text-emerald-400' },
  delayed: { label: 'Delayed', icon: Clock, className: 'text-amber-400' },
  closed: { label: 'Closed', icon: Moon, className: 'text-muted-foreground' },
  daily: { label: 'Official TRM', icon: Landmark, className: 'text-foreground' },
}

export function isLoading(ind: MacroIndicator, stale: boolean) {
  return ind.value === null && !ind.error && !stale
}

export function CardLabel({ label, ind }: { label: string; ind: MacroIndicator }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
      {ind.contract && ind.contract !== label && (
        <span className="text-xs text-muted-foreground">
          {ind.contract_month ? `${fmtContractMonth(ind.contract_month)} · ` : ''}
          {ind.contract}
        </span>
      )}
    </div>
  )
}

export function ChangeLine({ ind, stale }: { ind: MacroIndicator; stale: boolean }) {
  const change = fmtChange(ind)
  const direction = ind.change_mode === 'bp' ? (ind.change_bp ?? 0) : (ind.change ?? 0)
  return (
    <span className="text-sm">
      {change ? (
        <span className={cn('tabular-nums', pnlClass(direction))}>{change}</span>
      ) : (
        <span className="text-muted-foreground">{isLoading(ind, stale) ? 'Loading…' : 'No change data'}</span>
      )}
      {ind.previous_close !== null && <span className="text-muted-foreground"> vs {fmtValue(ind, ind.previous_close)} prev. close</span>}
    </span>
  )
}

export function FreshnessRow({ ind, stale }: { ind: MacroIndicator; stale: boolean }) {
  const fresh = stale ? { label: 'Stale', icon: WifiOff, className: 'text-muted-foreground' } : FRESHNESS[ind.freshness]
  return (
    <div className="flex flex-wrap items-center gap-x-1.5 text-xs">
      <fresh.icon className={cn('h-3.5 w-3.5 shrink-0', fresh.className)} />
      <span className={fresh.className}>{fresh.label}</span>
      {!stale && ind.freshness === 'delayed' && typeof ind.delay_minutes === 'number' && ind.delay_minutes >= 2 && (
        <span className={fresh.className}>· {fmtDelay(ind.delay_minutes)}</span>
      )}
      {ind.updated_at && <span className="text-muted-foreground">· updated {fmtUpdated(ind.updated_at)} ET</span>}
      {ind.valid_from && ind.valid_to && (
        <span className="text-muted-foreground">
          · valid {ind.valid_from === ind.valid_to ? fmtDay(ind.valid_from) : `${fmtDay(ind.valid_from)} – ${fmtDay(ind.valid_to)}`}
        </span>
      )}
    </div>
  )
}

export function ErrorRow({ error }: { error: string | null }) {
  if (!error) return null
  return (
    <p className="flex items-start gap-1.5 text-xs text-red-400">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{error}</span>
    </p>
  )
}
