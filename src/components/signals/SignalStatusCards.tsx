import { Activity, Bot, PlugZap } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { PROVIDER_LABELS } from './format'
import type { SignalStatus } from '@/types'

type Tone = 'good' | 'warn' | 'bad' | 'muted'

const TONE_DOT: Record<Tone, string> = {
  good: 'bg-emerald-400',
  warn: 'bg-amber-400',
  bad: 'bg-red-400',
  muted: 'bg-zinc-500',
}

function StatusCard({
  icon: Icon,
  label,
  value,
  tone,
  detail,
}: {
  icon: React.ElementType
  label: string
  value: string
  tone: Tone
  detail?: string | null
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1.5 p-4">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </div>
        <div className="flex items-center gap-2 text-sm font-semibold">
          <span className={cn('h-2 w-2 shrink-0 rounded-full', TONE_DOT[tone])} />
          {value}
        </div>
        {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
      </CardContent>
    </Card>
  )
}

export function SignalStatusCards({ status, socketOpen }: { status: SignalStatus | null; socketOpen: boolean }) {
  if (!socketOpen || !status) {
    return (
      <div className="grid grid-cols-3 gap-3">
        <StatusCard icon={PlugZap} label="IB Gateway" value="Backend unreachable" tone="bad" />
        <StatusCard icon={Activity} label="Market data" value="—" tone="muted" />
        <StatusCard icon={Bot} label="LLM filter" value="—" tone="muted" />
      </div>
    )
  }

  const ib: Record<SignalStatus['ib'], [string, Tone]> = {
    connected: ['Connected', 'good'],
    reconnecting: ['Reconnecting…', 'warn'],
    down: ['Down', 'bad'],
  }
  const stream: Record<SignalStatus['stream'], [string, Tone]> = {
    streaming: [`Streaming ${status.symbol} · ${status.timeframe_minutes}-min bars`, 'good'],
    warming_up: ['Loading history…', 'warn'],
    error: ['Error', 'bad'],
    idle: ['Waiting for connection', 'muted'],
  }
  const { llm } = status
  const provider = llm.provider ? PROVIDER_LABELS[llm.provider] ?? llm.provider : null
  const [llmValue, llmTone, llmDetail]: [string, Tone, string | null] = !llm.enabled
    ? ['Off', 'muted', 'Every signal is notified']
    : llm.configured
      ? [`On · ${provider}`, 'good', llm.model]
      : ['On · no AI provider', 'warn', 'Signals pass through unfiltered until one is set up in Settings']

  return (
    <div className="grid grid-cols-3 gap-3">
      <StatusCard icon={PlugZap} label="IB Gateway" value={ib[status.ib][0]} tone={ib[status.ib][1]} />
      <StatusCard
        icon={Activity}
        label="Market data"
        value={stream[status.stream][0]}
        tone={stream[status.stream][1]}
        detail={status.error}
      />
      <StatusCard icon={Bot} label="LLM filter" value={llmValue} tone={llmTone} detail={llmDetail} />
    </div>
  )
}
