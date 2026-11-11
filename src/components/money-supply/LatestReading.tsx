import { AlertTriangle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { fmtDay, fmtDollars, fmtMonth, fmtPct } from './format'
import type { MoneySupplyState } from '@/types'

function Change({ label, change, pct }: { label: string; change: number | null; pct: number | null }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      {change === null || pct === null ? (
        <span className="text-sm text-muted-foreground">Not available</span>
      ) : (
        <span className="text-sm font-medium tabular-nums">
          <span className={cn(pct < 0 && 'text-red-400')}>{fmtPct(pct)}</span>{' '}
          <span className="text-muted-foreground">({fmtDollars(change, true)})</span>
        </span>
      )}
    </div>
  )
}

export function LatestReading({ state }: { state: MoneySupplyState }) {
  const latest = state.latest
  if (!latest) return null
  const fetched = state.fetched_at ? new Date(state.fetched_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : null

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-6">
        <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs text-muted-foreground">M2, {fmtMonth(latest.month)}</span>
            <span className="text-3xl font-semibold tabular-nums">{fmtDollars(latest.value)}</span>
          </div>
          <Change label="vs. previous month" change={latest.mom_change} pct={latest.mom_pct} />
          <Change label="vs. a year earlier" change={latest.yoy_change} pct={latest.yoy_pct} />
        </div>
        <p className="text-xs text-muted-foreground">
          {state.units}. Source: Federal Reserve H.6 via FRED ({state.series}).
          {state.last_updated && <> FRED updated it {fmtDay(state.last_updated)}.</>}
          {state.next_release && <> Next release {fmtDay(state.next_release)}.</>}
        </p>
        {state.status === 'error' && state.error && (
          <p className="flex items-start gap-1.5 text-xs text-red-400">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              {state.error}.{fetched && ` Showing data saved ${fetched}.`} Retrying within an hour.
            </span>
          </p>
        )}
      </CardContent>
    </Card>
  )
}
