import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { Sparkline } from './Sparkline'
import { fmtTime, fmtValue } from './format'
import { CardLabel, ChangeLine, ErrorRow, FreshnessRow, isLoading } from './parts'
import type { MacroIndicator } from '@/types'

interface Props {
  label: string
  futures: MacroIndicator
  spot: MacroIndicator
  stale: (ind: MacroIndicator) => boolean
}

export function IndexCard({ label, futures, spot, stale }: Props) {
  const format = (v: number) => fmtValue(futures, v)
  const futuresStale = stale(futures)
  const spotStale = stale(spot)

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <CardLabel label={label} ind={futures} />

        <div className={cn('flex flex-col gap-0.5', futuresStale && 'opacity-60')}>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold">{futures.value === null ? '—' : format(futures.value)}</span>
            {futures.value !== null && <span className="text-xs text-muted-foreground">{futures.unit} · Futures</span>}
          </div>
          <ChangeLine ind={futures} stale={futuresStale} />
        </div>

        {/* Futures trade nearly around the clock, so their line stays useful when the index is closed. */}
        <Sparkline
          points={futures.sparkline}
          previousClose={futures.previous_close}
          format={format}
          formatTime={(t) => `${fmtTime(t)} ET`}
          label={futures.label}
          emptyText={isLoading(futures, futuresStale) ? '' : 'No history yet'}
        />

        <FreshnessRow ind={futures} stale={futuresStale} />
        <ErrorRow error={futures.error} />

        <Separator />

        <div className="flex flex-col gap-1.5">
          <div className={cn('flex flex-col gap-0.5', spotStale && 'opacity-60')}>
            <div className="flex items-baseline gap-1.5">
              <span className="text-lg font-semibold">{spot.value === null ? '—' : fmtValue(spot, spot.value)}</span>
              <span className="text-xs text-muted-foreground">
                {spot.value !== null && `${spot.unit} · `}Index{spot.contract ? ` · ${spot.contract}` : ''}
              </span>
            </div>
            <ChangeLine ind={spot} stale={spotStale} />
          </div>
          <FreshnessRow ind={spot} stale={spotStale} />
          <ErrorRow error={spot.error} />
        </div>
      </CardContent>
    </Card>
  )
}
