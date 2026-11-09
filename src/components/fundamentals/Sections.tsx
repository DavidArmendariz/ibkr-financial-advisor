import { useState } from 'react'
import { ExternalLink, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import * as api from '@/lib/api'
import { cn } from '@/lib/utils'
import { dateTime, newsTime, percent } from './format'
import type { FundamentalsError } from '@/hooks/useFundamentals'
import type { AnalystRatingMonth, FundamentalsNews, FundamentalsQuality, FundamentalsWriteUp } from '@/types'

export function QualityGrid({ items }: { items: FundamentalsQuality[] }) {
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {items.map((q) => (
        <div key={q.key} className="rounded-md border border-border p-3">
          <dt className="text-xs text-muted-foreground">{q.label}</dt>
          <dd className={cn('mt-1 text-base tabular-nums', q.value !== null && q.unit === '%' && q.value < 0 && 'text-red-400')}>
            {q.value === null ? '—' : q.unit === '%' ? percent(q.value) : `${q.value.toFixed(2)}×`}
          </dd>
        </div>
      ))}
    </dl>
  )
}

const RATING_ROWS: { key: keyof AnalystRatingMonth; label: string }[] = [
  { key: 'strong_buy', label: 'Strong buy' },
  { key: 'buy', label: 'Buy' },
  { key: 'hold', label: 'Hold' },
  { key: 'sell', label: 'Sell' },
  { key: 'strong_sell', label: 'Strong sell' },
]

const month = (period: string) => new Date(`${period}T00:00:00Z`).toLocaleDateString(undefined, { month: 'short', year: 'numeric', timeZone: 'UTC' })

export function Ratings({ ratings }: { ratings: { latest: AnalystRatingMonth; previous: AnalystRatingMonth | null } | null }) {
  if (!ratings) return <p className="text-sm text-muted-foreground">No analyst ratings reported.</p>
  const { latest, previous } = ratings
  const share = (r: AnalystRatingMonth | null) => (r?.buy_share == null ? '—' : `${Math.round(r.buy_share * 100)}%`)
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">
        <span className="text-lg font-semibold tabular-nums">{share(latest)}</span>{' '}
        <span className="text-muted-foreground">
          of {latest.total} analysts rate it buy or strong buy{previous ? `, against ${share(previous)} the month before` : ''}.
        </span>
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-muted-foreground">
              <th scope="col" className="px-3 py-2 text-left font-medium">Rating</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">{month(latest.period)}</th>
              {previous && <th scope="col" className="px-3 py-2 text-right font-medium">{month(previous.period)}</th>}
            </tr>
          </thead>
          <tbody>
            {RATING_ROWS.map((r) => (
              <tr key={r.key} className="border-b border-border last:border-0">
                <th scope="row" className="px-3 py-1.5 text-left font-normal text-muted-foreground">{r.label}</th>
                <td className="px-3 py-1.5 text-right tabular-nums">{latest[r.key]}</td>
                {previous && <td className="px-3 py-1.5 text-right tabular-nums text-muted-foreground">{previous[r.key]}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">Price targets aren't included on the free Finnhub plan. Analyst target changes show up in the news below.</p>
    </div>
  )
}

function NewsItem({ item }: { item: FundamentalsNews }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState<string | null | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)

  const toggle = async () => {
    setOpen((o) => !o)
    if (text !== undefined || !item.article_id) return
    try {
      setText((await api.getNewsArticle(item.provider, item.article_id)).text)
    } catch {
      setError("Couldn't load this article from IBKR.")
    }
  }

  return (
    <li className="flex flex-col gap-1 border-b border-border py-2 last:border-0">
      <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-foreground">
        <span className="tabular-nums">{newsTime(item.time)}</span>
        <span>{item.source}</span>
      </div>
      {item.url ? (
        <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1.5 text-sm hover:underline">
          {item.headline}
          <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-label="Opens in your browser" />
        </a>
      ) : item.article_id ? (
        <button type="button" onClick={toggle} aria-expanded={open} className="no-drag text-left text-sm hover:underline">
          {item.headline}
        </button>
      ) : (
        <span className="text-sm">{item.headline}</span>
      )}
      {open && (
        <div className="whitespace-pre-line rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
          {error ?? (text === undefined ? 'Loading…' : text || "This article can't be shown as text.")}
        </div>
      )}
    </li>
  )
}

export function NewsList({ items, notes }: { items: FundamentalsNews[]; notes: string[] }) {
  return (
    <div className="flex flex-col gap-2">
      {notes.map((n) => (
        <p key={n} className="text-xs text-amber-400">
          {n}
        </p>
      ))}
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No headlines in the last week.</p>
      ) : (
        <ul className="rounded-lg border border-border px-3">
          {items.map((n) => (
            <NewsItem key={`${n.provider}-${n.article_id ?? n.url ?? n.headline}`} item={n} />
          ))}
        </ul>
      )}
    </div>
  )
}

const WRITE_UP: { key: keyof FundamentalsWriteUp; label: string }[] = [
  { key: 'bull_case', label: 'Bull case' },
  { key: 'bear_case', label: 'Bear case' },
  { key: 'valuation_view', label: 'Valuation' },
  { key: 'watch', label: 'What to watch' },
]

interface WriteUpProps {
  analysis: FundamentalsWriteUp | null
  writing: boolean
  error: FundamentalsError | null
  onWrite: () => void
  onOpenSettings: () => void
}

export function WriteUpPanel({ analysis, writing, error, onWrite, onOpenSettings }: WriteUpProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" variant="outline" onClick={onWrite} disabled={writing} className="no-drag">
          <Sparkles className="h-3.5 w-3.5" />
          {writing ? 'Writing…' : analysis ? 'Write again' : 'Write AI summary'}
        </Button>
        <span className="text-xs text-muted-foreground">Sends this stock's figures and headlines to your AI provider. Never your account or positions.</span>
      </div>
      {error && (
        <p className="text-sm text-red-400">
          {error.message}{' '}
          {error.code === 'no_provider' && (
            <button type="button" onClick={onOpenSettings} className="no-drag underline">
              Open Settings
            </button>
          )}
        </p>
      )}
      {analysis && (
        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <dl className="grid gap-3 md:grid-cols-2">
            {WRITE_UP.map((w) => (
              <div key={w.key}>
                <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{w.label}</dt>
                <dd className="mt-1 text-sm">{analysis[w.key]}</dd>
              </div>
            ))}
          </dl>
          <p className="text-xs text-muted-foreground">
            Written {dateTime(analysis.created_at)} by {analysis.provider} ({analysis.model}) from data fetched {dateTime(analysis.data_time)}.
          </p>
        </div>
      )}
    </div>
  )
}
