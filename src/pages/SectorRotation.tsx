import { useEffect, useState } from 'react'
import { ErrorRow } from '@/components/macro/parts'
import { RotationGraph } from '@/components/rotation/RotationGraph'
import { RotationTable } from '@/components/rotation/RotationTable'
import { sessionDate } from '@/components/rotation/format'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useRotation } from '@/hooks/useRotation'
import type { RotationTimeframe } from '@/types'

const TIMEFRAMES: { value: RotationTimeframe; label: string }[] = [
  { value: 'weekly', label: 'Weekly' },
  { value: 'daily', label: 'Daily' },
]
const TAIL_MIN = 3
const TAIL_MAX = 20

export function SectorRotationPage() {
  const { state, unreachable, saveError, update } = useRotation()
  const [selected, setSelected] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [tailDraft, setTailDraft] = useState<number | ''>('')
  const settings = state?.settings
  const tail = settings?.tail ?? 8
  const timeframe = settings?.timeframe ?? 'weekly'
  const active = hovered ?? selected

  useEffect(() => {
    if (settings) setTailDraft(settings.tail)
  }, [settings?.tail]) // eslint-disable-line react-hooks/exhaustive-deps

  const changeTail = (value: number | '') => {
    setTailDraft(value)
    if (value !== '' && Number.isInteger(value) && value >= TAIL_MIN && value <= TAIL_MAX && value !== tail) update({ tail: value })
  }

  const stale = unreachable || state?.stale
  const plotted = state?.etfs.filter((e) => e[timeframe].points.length > 0).length ?? 0

  return (
    <ScrollArea className="h-full">
      <div className="flex max-w-5xl flex-col gap-5 p-6">
        <div>
          <h1 className="text-lg font-semibold">Sector Rotation</h1>
          <p className="text-sm text-muted-foreground">
            Where money is moving between sectors. Each trail is a sector ETF against SPY: right of centre it's beating the market, above centre that
            lead is growing. Sectors usually rotate clockwise, from Improving to Leading, Weakening, then Lagging.
          </p>
        </div>

        {unreachable && <p className="text-sm text-red-400">Backend unreachable. Showing the last readings received.</p>}
        {!unreachable && state?.connected === false && (
          <p className="text-sm text-amber-400">
            Not connected to IBKR. {state.stale ? 'Showing the last readings, which may be out of date.' : 'Readings will load once connected.'}
          </p>
        )}
        {state?.benchmark.error && (
          <div className="flex flex-col gap-1">
            <p className="text-sm text-red-400">Couldn't get SPY, the benchmark, so readings can't be updated.</p>
            <ErrorRow error={state.benchmark.error} />
          </div>
        )}

        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            <span>Timeframe</span>
            <div className="no-drag flex gap-1" role="group" aria-label="Timeframe">
              {TIMEFRAMES.map((o) => (
                <Button
                  key={o.value}
                  size="sm"
                  variant={timeframe === o.value ? 'default' : 'outline'}
                  aria-pressed={timeframe === o.value}
                  disabled={!state}
                  onClick={() => update({ timeframe: o.value })}
                >
                  {o.label}
                </Button>
              ))}
            </div>
          </div>
          <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            <span>
              Trail length ({TAIL_MIN}–{TAIL_MAX} {timeframe === 'weekly' ? 'weeks' : 'days'})
            </span>
            <Input
              type="number"
              min={TAIL_MIN}
              max={TAIL_MAX}
              step={1}
              value={tailDraft}
              disabled={!state}
              onChange={(e) => changeTail(Number.isNaN(e.target.valueAsNumber) ? '' : e.target.valueAsNumber)}
              onBlur={() => setTailDraft(tail)}
              className="w-24 tabular-nums"
            />
          </label>
          {state?.last_session != null && (
            <p className="ml-auto text-xs text-muted-foreground">
              Completed sessions through {sessionDate(state.last_session)}
              {timeframe === 'weekly' ? ', the latest week may be partial' : ''}
            </p>
          )}
        </div>
        {saveError && <p className="text-xs text-amber-400">{saveError}</p>}

        {!state ? (
          <p className="text-sm text-muted-foreground">{unreachable ? '' : 'Loading…'}</p>
        ) : (
          <>
            <section aria-label="Rotation graph" className={stale ? 'opacity-60' : undefined}>
              {plotted === 0 && state.connected && !state.benchmark.error ? (
                <p className="text-sm text-muted-foreground">Fetching two years of daily bars for SPY and 12 ETFs…</p>
              ) : (
                // Below this width the labels get too small to read, so it scrolls instead.
                <div className="overflow-x-auto">
                  <div className="min-w-[560px]">
                    <RotationGraph etfs={state.etfs} timeframe={timeframe} tail={tail} active={active} onHover={setHovered} />
                  </div>
                </div>
              )}
            </section>

            <section aria-label="Rotation table" className="flex flex-col gap-2">
              <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">By quadrant</h2>
              <RotationTable
                etfs={state.etfs}
                timeframe={timeframe}
                active={active}
                selected={selected}
                onSelect={setSelected}
                onHover={setHovered}
              />
            </section>
          </>
        )}

        <p className="text-xs text-muted-foreground">
          RS-Ratio and RS-Momentum here are the app's own approximation of the Relative Rotation Graph method, not the official JdK values, so they
          won't match StockCharts or TradingView exactly. Both are centred on 100 over a {state?.lookback ?? 10}-period lookback. Context only: this
          view raises no alerts.
        </p>
      </div>
    </ScrollArea>
  )
}
