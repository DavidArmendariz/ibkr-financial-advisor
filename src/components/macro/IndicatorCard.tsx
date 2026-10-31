import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { Sparkline } from './Sparkline'
import { fmtTime, fmtValue } from './format'
import { CardLabel, ChangeLine, ErrorRow, FreshnessRow, isLoading } from './parts'
import type { MacroIndicator } from '@/types'

export function IndicatorCard({ ind, stale }: { ind: MacroIndicator; stale: boolean }) {
  const format = (v: number) => fmtValue(ind, v)
  // Daily points sit at midnight Bogotá; a calendar day reads better than a time.
  const formatTime =
    ind.freshness === 'daily'
      ? (t: number) => new Date(t * 1000).toLocaleDateString('en-US', { timeZone: 'America/Bogota', month: 'short', day: 'numeric' })
      : (t: number) => `${fmtTime(t)} ET`

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <CardLabel label={ind.label} ind={ind} />

        <div className={cn('flex flex-col gap-0.5', stale && 'opacity-60')}>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold">{ind.value === null ? '—' : format(ind.value)}</span>
            {ind.unit !== '%' && ind.value !== null && <span className="text-xs text-muted-foreground">{ind.unit}</span>}
          </div>
          <ChangeLine ind={ind} stale={stale} />
        </div>

        <Sparkline
          points={ind.sparkline}
          previousClose={ind.previous_close}
          format={format}
          formatTime={formatTime}
          label={ind.label}
          emptyText={isLoading(ind, stale) ? '' : 'No history yet'}
        />

        <FreshnessRow ind={ind} stale={stale} />
        <ErrorRow error={ind.error} />
      </CardContent>
    </Card>
  )
}
