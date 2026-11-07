import { AlertTriangle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import type { PlannerQuote } from '@/types'

export const money = (n: number | null | undefined, digits = 2) =>
  typeof n === 'number' ? `$${n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}` : '—'

const pct = (n: number | null) => (n === null ? '' : ` · ${n.toFixed(2)}%`)

export const timeET = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString('en-US', { timeZone: 'America/New_York', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }) + ' ET'
    : '—'

export function AtrCard({ quote, intradayLabel, dailyLabel }: { quote: PlannerQuote; intradayLabel: string; dailyLabel: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-baseline justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{quote.symbol}</span>
          <span className="text-xs text-muted-foreground">last {timeET(quote.price_time)} · quote {timeET(quote.quote_time)}</span>
        </div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <span className="text-2xl font-semibold tabular-nums">{money(quote.price)}</span>
          <span className="text-sm tabular-nums text-muted-foreground">
            bid <span className="text-foreground">{money(quote.bid)}</span> · ask <span className="text-foreground">{money(quote.ask)}</span>
            {quote.quote_delayed && <span className="ml-1 text-amber-400">delayed</span>}
          </span>
        </div>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">{intradayLabel}</dt>
            <dd className="tabular-nums">
              {money(quote.intraday_atr, 3)}
              <span className="text-muted-foreground">{pct(quote.intraday_pct)}</span>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">{dailyLabel}</dt>
            <dd className="tabular-nums">
              {money(quote.daily_atr)}
              <span className="text-muted-foreground">{pct(quote.daily_pct)}</span>
            </dd>
          </div>
        </dl>
        {quote.error && (
          <p className="flex items-start gap-1.5 text-xs text-red-400">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{quote.error}</span>
          </p>
        )}
      </CardContent>
    </Card>
  )
}
