import { ScrollArea } from '@/components/ui/scroll-area'
import { IndicatorCard } from '@/components/macro/IndicatorCard'
import { useMacro } from '@/hooks/useMacro'

export function MacroPage() {
  const { state, unreachable } = useMacro()

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h1 className="text-lg font-semibold">Macro</h1>
          <p className="text-sm text-muted-foreground">
            Commodity and equity futures, rates, volatility and the main US indexes from IBKR, against the previous close; futures follow the
            front month. USD/COP is Banco de la República's official daily rate (TRM).
          </p>
        </div>

        {unreachable && <p className="text-sm text-red-400">Backend unreachable. Showing the last values received.</p>}
        {!unreachable && state?.connected === false && (
          <p className="text-sm text-amber-400">Not connected to IBKR. Showing the last values received.</p>
        )}

        {state && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {state.indicators.map((ind) => (
              <IndicatorCard key={ind.key} ind={ind} stale={unreachable || ind.stale} />
            ))}
          </div>
        )}
      </div>
    </ScrollArea>
  )
}
