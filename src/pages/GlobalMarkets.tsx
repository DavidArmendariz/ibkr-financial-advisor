import { ChipStockTable } from '@/components/global-markets/ChipStockTable'
import { MarketCard } from '@/components/global-markets/MarketCard'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useGlobalMarkets } from '@/hooks/useGlobalMarkets'
import type { GlobalInstrument } from '@/types'

const GRID = 'grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3'

export function GlobalMarketsPage() {
  const { state, unreachable } = useGlobalMarkets()
  const instruments = state?.instruments ?? []
  const stale = (m: GlobalInstrument) => unreachable || m.stale
  const indexes = instruments.filter((m) => m.section === 'Indexes')
  const stocks = instruments.filter((m) => m.section !== 'Indexes')

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-6 p-6">
        <div>
          <h1 className="text-lg font-semibold">Asia &amp; Europe</h1>
          <p className="text-sm text-muted-foreground">
            Indexes and chip stocks on their home markets from IBKR, in local currency, against the previous close. Refreshed from 5-minute bars, so
            data can lag by a different amount per market: each card and row shows when its data is from.
          </p>
        </div>

        {unreachable && <p className="text-sm text-red-400">Backend unreachable. Showing the last values received.</p>}
        {!unreachable && state?.connected === false && (
          <p className="text-sm text-amber-400">Not connected to IBKR. Showing the last values received.</p>
        )}

        {indexes.length > 0 && (
          <section aria-label="Indexes" className="flex flex-col gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">Indexes</h2>
            <div className={GRID}>
              {indexes.map((m) => (
                <MarketCard key={m.key} market={m} stale={stale(m)} />
              ))}
            </div>
          </section>
        )}

        {stocks.length > 0 && (
          <section aria-label="Chip stocks" className="flex flex-col gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">Chip stocks</h2>
            <ChipStockTable stocks={stocks} stale={stale} />
          </section>
        )}
      </div>
    </ScrollArea>
  )
}
