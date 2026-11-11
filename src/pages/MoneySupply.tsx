import { AlertTriangle } from 'lucide-react'
import { LatestReading } from '@/components/money-supply/LatestReading'
import { M2Charts } from '@/components/money-supply/M2Charts'
import { M2Explainer } from '@/components/money-supply/M2Explainer'
import { calcCutoff } from '@/components/money-supply/range'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useMoneySupply } from '@/hooks/useMoneySupply'
import type { MoneySupplyRange } from '@/types'

const RANGES: { value: MoneySupplyRange; label: string }[] = [
  { value: '5y', label: '5Y' },
  { value: '10y', label: '10Y' },
  { value: '25y', label: '25Y' },
  { value: 'all', label: 'All' },
]

export function MoneySupplyPage({ onOpenSettings }: { onOpenSettings: () => void }) {
  const { state, unreachable, range, setRange } = useMoneySupply()
  const observations = state?.observations ?? []
  const cutoff = calcCutoff(observations.at(-1)?.month, range)
  const shown = cutoff ? observations.filter((o) => o.month >= cutoff) : observations

  return (
    <ScrollArea className="h-full">
      <div className="flex max-w-6xl flex-col gap-5 p-6">
        <div>
          <h1 className="text-lg font-semibold">M2 Money Supply</h1>
          <p className="text-sm text-muted-foreground">
            How much money US households and businesses hold, and how fast it's growing. A gauge of liquidity for context: it doesn't raise alerts.
          </p>
        </div>

        {unreachable && <p className="text-sm text-red-400">Backend unreachable. Showing the last data received.</p>}

        {state?.status === 'no_key' && (
          <p className="text-sm text-amber-400">
            M2 data comes from FRED and needs a free FRED API key, the same one the Calendar uses.{' '}
            <button type="button" onClick={onOpenSettings} className="no-drag underline">
              Open Settings
            </button>
          </p>
        )}
        {state?.status === 'loading' && <p className="text-sm text-muted-foreground">Loading M2 from FRED…</p>}
        {state?.status === 'error' && !state.latest && (
          <p className="flex items-start gap-1.5 text-sm text-red-400">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{state.error}. Retrying within an hour.</span>
          </p>
        )}

        {state?.latest && state.status !== 'no_key' && (
          <>
            <LatestReading state={state} />
            <div className="no-drag flex items-center gap-1" role="group" aria-label="Chart range">
              <span className="mr-2 text-xs text-muted-foreground">Range</span>
              {RANGES.map((o) => (
                <Button key={o.value} size="sm" variant={range === o.value ? 'default' : 'outline'} aria-pressed={range === o.value} onClick={() => setRange(o.value)}>
                  {o.label}
                </Button>
              ))}
            </div>
            <M2Charts observations={shown} />
          </>
        )}

        <M2Explainer />
      </div>
    </ScrollArea>
  )
}
