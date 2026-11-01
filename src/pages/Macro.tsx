import { ScrollArea } from '@/components/ui/scroll-area'
import { IndexCard } from '@/components/macro/IndexCard'
import { IndicatorCard } from '@/components/macro/IndicatorCard'
import { MACRO_SECTIONS, type MacroCardLayout } from '@/components/macro/sections'
import { SentimentCard } from '@/components/macro/SentimentCard'
import { useMacro } from '@/hooks/useMacro'
import type { MacroIndicator } from '@/types'

export function MacroPage() {
  const { state, unreachable } = useMacro()
  const indicators = state?.indicators ?? []
  const byKey = new Map(indicators.map((ind) => [ind.key, ind]))
  const isStale = (ind: MacroIndicator) => unreachable || ind.stale

  const renderCard = (card: MacroCardLayout) => {
    if (typeof card === 'string') {
      const ind = byKey.get(card)
      return ind && <IndicatorCard key={card} ind={ind} stale={isStale(ind)} />
    }
    const futures = byKey.get(card.futures)
    const spot = byKey.get(card.spot)
    return futures && spot && <IndexCard key={card.label} label={card.label} futures={futures} spot={spot} stale={isStale} />
  }

  // A new backend indicator must show up even if nobody added it to the layout.
  const placed = new Set(MACRO_SECTIONS.flatMap(({ cards }) => cards.flatMap((c) => (typeof c === 'string' ? [c] : [c.futures, c.spot]))))
  const unplaced = indicators.filter((ind) => !placed.has(ind.key))
  const sections = unplaced.length > 0 ? [...MACRO_SECTIONS, { label: 'Other', cards: unplaced.map((ind) => ind.key) }] : MACRO_SECTIONS

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-6 p-6">
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

        {state?.sentiment && <SentimentCard sentiment={state.sentiment} stale={unreachable || state.sentiment.stale} />}

        {state &&
          sections.map(({ label, cards }) => (
            <section key={label} aria-label={label} className="flex flex-col gap-2">
              <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">{label}</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">{cards.map(renderCard)}</div>
            </section>
          ))}
      </div>
    </ScrollArea>
  )
}
