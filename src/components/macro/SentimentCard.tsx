import { useState } from 'react'
import { AlertTriangle, ChevronDown, WifiOff } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { Sparkline } from './Sparkline'
import { fmtDay } from './format'
import type { MarketSentiment, SentimentComponent } from '@/types'

const BAR = '#3987e5'

const fmtScore = (v: number) => Math.round(v).toString()
const fmtDate = (t: number) => new Date(t * 1000).toLocaleDateString('en-US', { timeZone: 'UTC', month: 'short', day: 'numeric' })

function Meter({ component }: { component: SentimentComponent }) {
  const { label, detail, score, error, in_score } = component
  return (
    <div title={detail}>
      <div className="flex items-baseline justify-between gap-2 text-xs">
        <span className="text-muted-foreground">
          {label}
          {!in_score && <span className="opacity-70"> · context only</span>}
        </span>
        <span className="tabular-nums">{score === null ? '—' : fmtScore(score)}</span>
      </div>
      <div className="relative mt-1 h-1.5 rounded-full bg-muted">
        {score !== null && <div className="h-full rounded-full" style={{ width: `${score}%`, background: BAR, opacity: in_score ? 1 : 0.5 }} />}
        <span aria-hidden className="absolute -top-0.5 left-1/2 h-2.5 w-px bg-muted-foreground/60" />
      </div>
      {error && (
        <p className="mt-1 flex items-start gap-1 text-xs text-red-400">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
          <span>{error}</span>
        </p>
      )}
    </div>
  )
}

const BANDS = [
  ['0–24', 'Extreme Fear'],
  ['25–44', 'Fear'],
  ['45–55', 'Neutral'],
  ['56–75', 'Greed'],
  ['76–100', 'Extreme Greed'],
]

function Explanation({ components }: { components: SentimentComponent[] }) {
  return (
    <div className="grid grid-cols-1 gap-5 border-t border-border pt-4 text-xs text-muted-foreground lg:grid-cols-[minmax(0,1fr)_minmax(0,2.2fr)]">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <h3 className="font-medium text-foreground">The score</h3>
          <p>
            Each component is ranked against its own last 252 trading days, about a year. A score of 90 means today's reading is at or above 90%
            of that year. The score is the simple average of the scored components, using daily closes.
          </p>
          <p>It describes the mood of the market. It isn't a buy or sell signal, and it hasn't been backtested.</p>
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
          {BANDS.map(([range, label]) => (
            <div key={label} className="contents">
              <dt className="tabular-nums">{range}</dt>
              <dd className="text-foreground">{label}</dd>
            </div>
          ))}
        </dl>
      </div>
      <dl className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {components.map((c) => (
          <div key={c.key}>
            <dt className="font-medium text-foreground">{c.label}</dt>
            <dd>{c.detail}</dd>
            <dd className="mt-0.5">{c.meaning}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export function SentimentCard({ sentiment, stale }: { sentiment: MarketSentiment; stale: boolean }) {
  const { score, band, as_of, components, history } = sentiment
  const scored = components.filter((c) => c.in_score)
  const unavailable = scored.filter((c) => c.score === null).length
  const [explained, setExplained] = useState(false)

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-4">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.2fr)]">
          <div className="flex flex-col gap-2">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Market sentiment</span>
            <div className={cn('flex items-baseline gap-2', stale && 'opacity-60')}>
              <span className="text-4xl font-semibold tabular-nums">{score === null ? '—' : fmtScore(score)}</span>
              <span className="text-sm font-medium">{band ?? 'No score available'}</span>
            </div>
            <p className="text-xs text-muted-foreground">Our own estimate from IBKR data, not CNN's Fear &amp; Greed Index.</p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {stale && <WifiOff className="h-3.5 w-3.5 shrink-0" />}
              {stale ? 'Stale · ' : ''}
              {as_of ? `Daily close, ${fmtDay(as_of)}` : 'Needs at least 3 components'}
              {score !== null && unavailable > 0 ? ` · ${scored.length - unavailable} of ${scored.length} components` : ''}
            </p>
          </div>

          <div className="flex flex-col justify-center gap-1">
            <span className="text-xs text-muted-foreground">Last {history.length || 60} trading days</span>
            <Sparkline points={history} previousClose={null} format={fmtScore} formatTime={fmtDate} label="Market sentiment score" emptyText="No history yet" />
          </div>

          <div className={cn('flex flex-col gap-2', stale && 'opacity-60')}>
            {components.map((c) => (
              <Meter key={c.key} component={c} />
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setExplained((open) => !open)}
          aria-expanded={explained}
          className="no-drag flex items-center gap-1 self-start text-xs text-muted-foreground hover:text-foreground"
        >
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', explained && 'rotate-180')} />
          How it's calculated
        </button>
        {explained && <Explanation components={components} />}
      </CardContent>
    </Card>
  )
}
