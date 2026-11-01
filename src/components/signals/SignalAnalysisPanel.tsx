import { useState } from 'react'
import axios from 'axios'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import * as api from '@/lib/api'
import { cn, pnlClass } from '@/lib/utils'
import type { PostMortem, PreMortem, SignalAnalysis, SignalAnalysisKind, SignalHistoryRecord } from '@/types'

const LABELS: Record<SignalAnalysisKind, string> = { pre: 'Pre-mortem', post: 'Post-mortem' }

function fmtPercent(value: number | null) {
  if (value === null) return 'n/a'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function Meta({ result }: { result: SignalAnalysis }) {
  const time = new Date(result.created_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
  return (
    <p className="text-[11px] text-muted-foreground">
      AI analysis, not advice · {result.provider} {result.model} · {time}
    </p>
  )
}

function Field({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="font-medium">{label}</p>
      <p className="text-muted-foreground">{text}</p>
    </div>
  )
}

function PreResult({ result }: { result: PreMortem }) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <p className="font-medium">
        Pre-mortem: {result.action === 'take' ? 'Take' : 'Skip'} · {Math.round(result.confidence * 100)}% confidence
      </p>
      <p className="text-muted-foreground">Uses only what was known when the signal fired.</p>
      <Field label="Case for" text={result.case_for} />
      <Field label="Risks" text={result.risks} />
      <Field label="What would prove it wrong" text={result.invalidation} />
      <Meta result={result} />
    </div>
  )
}

function Figure({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={cn('tabular-nums', value !== null && pnlClass(value))}>{fmtPercent(value)}</dd>
    </div>
  )
}

function PostResult({ result }: { result: PostMortem }) {
  const { return_pct: r, largest_gain_pct, largest_loss_pct, returned_to_start } = result.outcomes
  const verdict = { good: 'Good idea', bad: 'Bad idea', mixed: 'Mixed' }[result.verdict]
  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <p className="font-medium">Post-mortem: {verdict}</p>
      <p className="text-muted-foreground">
        Written with hindsight, as a {result.directions.join(' and ')} entry at the signal's price, before costs.
      </p>
      <dl className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        <Figure label="15 min" value={r['15m']} />
        <Figure label="30 min" value={r['30m']} />
        <Figure label="60 min" value={r['60m']} />
        <Figure label="Close" value={r.close} />
        <Figure label="Largest gain" value={largest_gain_pct} />
        <Figure label="Largest loss" value={largest_loss_pct} />
      </dl>
      <p className="text-muted-foreground">
        Figures are for a long entry. {result.directions.includes('short') ? 'A short is the opposite. ' : ''}
        {returned_to_start ? 'Price came back to the signal level.' : "Price didn't come back to the signal level."}
      </p>
      <p>{result.explanation}</p>
      <Meta result={result} />
    </div>
  )
}

function OutcomeFigures({ outcome }: { outcome: SignalHistoryRecord['outcome'] }) {
  if (!outcome) return <p className="text-muted-foreground">Outcome pending</p>
  if (outcome.status === 'not_available') return <p className="text-muted-foreground">Outcome not available</p>
  return (
    <dl className="grid grid-cols-3 gap-2 sm:grid-cols-5" aria-label="Signal outcome">
      <Figure label="After 5 min" value={outcome.move_5m} />
      <Figure label="After 15 min" value={outcome.move_15m} />
      <Figure label="After 30 min" value={outcome.move_30m} />
      <Figure label="Largest up" value={outcome.max_up} />
      <Figure label="Largest down" value={outcome.max_down} />
    </dl>
  )
}

export function SignalAnalysisPanel({ signal }: { signal: SignalHistoryRecord }) {
  const [saved, setSaved] = useState(signal.analyses ?? {})
  const [running, setRunning] = useState<SignalAnalysisKind[]>([])
  const [error, setError] = useState<string | null>(null)

  const run = async (kind: SignalAnalysisKind) => {
    setRunning((now) => [...now, kind])
    setError(null)
    try {
      const result = await api.runSignalAnalysis(signal.id, kind)
      setSaved((now) => ({ ...now, [kind]: result }))
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null
      setError(typeof detail === 'string' ? detail : `${LABELS[kind]} failed`)
    } finally {
      setRunning((now) => now.filter((k) => k !== kind))
    }
  }

  return (
    <div className="flex flex-col gap-2 text-xs">
      <OutcomeFigures outcome={signal.outcome} />
      <div className="no-drag flex flex-wrap items-center gap-2">
        {(['pre', 'post'] as const).map((kind) => (
          <Button key={kind} variant="outline" size="sm" className="h-7 gap-1.5 text-xs" disabled={running.includes(kind)} onClick={() => run(kind)}>
            {running.includes(kind) && <Loader2 className="h-3 w-3 animate-spin" />}
            {running.includes(kind) ? 'Analyzing…' : saved[kind] ? `Run ${LABELS[kind]} again` : LABELS[kind]}
          </Button>
        ))}
      </div>
      {error && (
        <p className="flex items-start gap-1.5 text-red-400">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </p>
      )}
      {(saved.pre || saved.post) && (
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
          {saved.pre && <PreResult result={saved.pre} />}
          {saved.post && <PostResult result={saved.post} />}
        </div>
      )}
    </div>
  )
}
