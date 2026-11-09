import { useState } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import { NewsList, QualityGrid, Ratings, WriteUpPanel } from '@/components/fundamentals/Sections'
import { ValuationTable } from '@/components/fundamentals/ValuationTable'
import { dateTime, marketCap, signedPercent } from '@/components/fundamentals/format'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useFundamentals } from '@/hooks/useFundamentals'
import { cn, pnlClass } from '@/lib/utils'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} className="flex flex-col gap-2">
      <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">{title}</h2>
      {children}
    </section>
  )
}

export function FundamentalsPage({ onOpenSettings }: { onOpenSettings: () => void }) {
  const { data, loading, error, writing, writeError, lookup, writeUp, initialTicker } = useFundamentals()
  const [ticker, setTicker] = useState(initialTicker)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (ticker.trim()) lookup(ticker)
  }

  return (
    <ScrollArea className="h-full">
      <div className="flex max-w-5xl flex-col gap-6 p-6">
        <div>
          <h1 className="text-lg font-semibold">Fundamentals</h1>
          <p className="text-sm text-muted-foreground">
            A US stock's valuation against its peers and its own history, its quality and growth, analyst ratings, and recent news.
          </p>
        </div>

        <form onSubmit={submit} className="flex flex-wrap items-center gap-2" role="search">
          <label htmlFor="fundamentals-ticker" className="sr-only">
            Ticker
          </label>
          <Input
            id="fundamentals-ticker"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Ticker, e.g. NVDA"
            maxLength={10}
            autoComplete="off"
            spellCheck={false}
            className="w-full uppercase tabular-nums sm:w-44"
          />
          <Button type="submit" size="sm" disabled={loading || !ticker.trim()} className="no-drag">
            <Search className="h-3.5 w-3.5" />
            Look up
          </Button>
          {data && (
            <Button type="button" size="sm" variant="outline" disabled={loading} onClick={() => lookup(data.ticker, true)} className="no-drag">
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              Refresh
            </Button>
          )}
          {loading && <span className="text-xs text-muted-foreground">Fetching figures, peers, and news…</span>}
        </form>

        {error && (
          <p className={cn('text-sm', error.code === 'not_found' || error.code === 'bad_ticker' ? 'text-muted-foreground' : 'text-red-400')}>
            {error.message}{' '}
            {error.code === 'no_key' && (
              <button type="button" onClick={onOpenSettings} className="no-drag underline">
                Open Settings
              </button>
            )}
            {error.code === 'rate_limited' && data && ' Showing the figures already loaded.'}
          </p>
        )}

        {!data && !loading && !error && <p className="text-sm text-muted-foreground">Enter a ticker to see its fundamentals.</p>}

        {data && (
          <>
            <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
              <div>
                <p className="text-xl font-semibold">
                  {data.ticker} <span className="font-normal text-muted-foreground">{data.name}</span>
                </p>
                <p className="text-sm text-muted-foreground">
                  {[data.industry, data.exchange].filter(Boolean).join(' · ')} · Market cap {marketCap(data.market_cap_millions)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xl font-semibold tabular-nums">
                  {data.price === null ? '—' : `${data.price.toFixed(2)} ${data.currency ?? ''}`}
                </p>
                {data.change_pct !== null && <p className={cn('text-sm tabular-nums', pnlClass(data.change_pct))}>{signedPercent(data.change_pct)} today</p>}
              </div>
            </div>

            <Section title="Valuation">
              <ValuationTable multiples={data.multiples} />
              <p className="text-xs text-muted-foreground">
                "Cheaper" means at least 20% below the median. Peers: {data.peers.length ? data.peers.join(', ') : 'none listed'}.
              </p>
            </Section>

            <Section title="Quality and growth">
              <QualityGrid items={data.quality} />
            </Section>

            <Section title="Analyst ratings">
              <Ratings ratings={data.ratings} />
            </Section>

            <Section title="AI summary">
              <WriteUpPanel analysis={data.analysis} writing={writing} error={writeError} onWrite={writeUp} onOpenSettings={onOpenSettings} />
            </Section>

            <Section title="News">
              <NewsList items={data.news} notes={data.news_notes} />
            </Section>

            <p className="text-xs text-muted-foreground">
              Figures and peers from Finnhub, fetched {dateTime(data.fetched_at)}; news from IBKR and Finnhub; the summary is written by an AI. None of
              it is investment advice, and this view never places orders.
            </p>
          </>
        )}
      </div>
    </ScrollArea>
  )
}
