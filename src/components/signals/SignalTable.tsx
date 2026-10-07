import { Bell, BellOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import { fmtPrice, fmtRatio, fmtTimeET } from './format'
import type { LLMDecision, SignalRecord } from '@/types'

const DECISION_STYLE: Record<LLMDecision['action'], string> = {
  take: 'bg-emerald-500/15 text-emerald-400',
  skip: 'bg-zinc-500/20 text-zinc-300',
  unfiltered: 'bg-amber-500/15 text-amber-400',
}

function Decision({ llm }: { llm: LLMDecision }) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium', DECISION_STYLE[llm.action])}>
      {llm.action}
      {llm.confidence !== null && <span className="tabular-nums opacity-80">{Math.round(llm.confidence * 100)}%</span>}
    </span>
  )
}

export function SignalTable({ signals }: { signals: SignalRecord[] }) {
  if (signals.length === 0) {
    return (
      <div className="rounded-lg border border-border py-10 text-center text-sm text-muted-foreground">
        No signals yet. Entries appear here as they fire during market hours.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th className="px-3 py-2 font-medium">Time (ET)</th>
            <th className="px-3 py-2 font-medium">Signal</th>
            <th className="px-3 py-2 text-right font-medium">Price</th>
            <th className="px-3 py-2 text-right font-medium">VWAP</th>
            <th className="px-3 py-2 text-right font-medium">EMA fast / slow</th>
            <th className="px-3 py-2 text-right font-medium">RVOL</th>
            <th className="px-3 py-2 font-medium">LLM</th>
            <th className="px-3 py-2 font-medium">Reason</th>
            <th className="px-3 py-2 font-medium" aria-label="Notified" />
          </tr>
        </thead>
        <tbody>
          {signals.map((s) => (
            <tr key={s.id} className="border-b border-border last:border-0">
              <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted-foreground">{fmtTimeET(s.time, true)}</td>
              <td className="whitespace-nowrap px-3 py-2 font-medium">{s.signal_type.replace(/_/g, ' ')}</td>
              <td className="px-3 py-2 text-right tabular-nums">{fmtPrice(s.price)}</td>
              <td className="px-3 py-2 text-right tabular-nums">{fmtPrice(s.indicators.vwap)}</td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                {fmtPrice(s.indicators.ema_fast)} / {fmtPrice(s.indicators.ema_slow)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">{fmtRatio(s.indicators.rvol)}</td>
              <td className="px-3 py-2">
                <Decision llm={s.llm} />
              </td>
              <td className="max-w-[280px] px-3 py-2 text-muted-foreground" title={s.llm.reason}>
                <span className="line-clamp-2">{s.llm.reason || '—'}</span>
              </td>
              <td className="px-3 py-2" title={s.notified ? 'Notification shown' : 'Filtered out, no notification'}>
                {s.notified ? (
                  <Bell className="h-3.5 w-3.5 text-foreground" />
                ) : (
                  <BellOff className="h-3.5 w-3.5 text-muted-foreground" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
