import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { SignalAnalysisPanel } from '@/components/signals/SignalAnalysisPanel'
import { SignalOutcomeResultsTable } from '@/components/signals/SignalOutcomeResults'
import { SignalTable } from '@/components/signals/SignalTable'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useSignalHistory } from '@/hooks/useSignalHistory'

const FILTERS: { label: string; type: string | null }[] = [
  { label: 'All', type: null },
  { label: 'Relative volume', type: 'VOLUME_SPIKE' },
  { label: 'EMA cross', type: 'EMA_CROSS' },
  { label: 'VWAP cross', type: 'VWAP_CROSS' },
  { label: 'VWAP band above', type: 'VWAP_BAND_ABOVE' },
  { label: 'VWAP band below', type: 'VWAP_BAND_BELOW' },
  { label: 'RSI above', type: 'RSI_ABOVE' },
  { label: 'RSI below', type: 'RSI_BELOW' },
]

export function SignalHistoryPage() {
  const [type, setType] = useState<string | null>(null)
  const { signals, loaded, unreachable, hasOlder, loadingOlder, loadOlder } = useSignalHistory(type)
  const empty = type ? 'No signals from this trigger yet' : 'No signals recorded yet'

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h1 className="text-lg font-semibold">Signal History</h1>
          <p className="text-sm text-muted-foreground">Every saved signal, newest first, including those the LLM filter skipped.</p>
        </div>

        <div className="no-drag flex flex-wrap gap-2" role="group" aria-label="Filter by trigger">
          {FILTERS.map((f) => (
            <Button key={f.label} size="sm" variant={type === f.type ? 'default' : 'outline'} aria-pressed={type === f.type} onClick={() => setType(f.type)}>
              {f.label}
            </Button>
          ))}
        </div>

        <SignalOutcomeResultsTable />

        {unreachable && <p className="text-sm text-red-400">Backend unreachable. This list may be out of date.</p>}
        {!loaded && !unreachable && <Placeholder text="Loading signals…" />}
        {loaded && signals.length === 0 && <Placeholder text={empty} />}
        {signals.length > 0 && <SignalTable signals={signals} renderDetails={(s) => <SignalAnalysisPanel signal={s} />} />}

        {hasOlder && (
          <Button variant="outline" size="sm" onClick={loadOlder} disabled={loadingOlder} className="no-drag gap-2 self-center">
            {loadingOlder && <Loader2 className="h-4 w-4 animate-spin" />}
            Load older
          </Button>
        )}
      </div>
    </ScrollArea>
  )
}

function Placeholder({ text }: { text: string }) {
  return <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">{text}</div>
}
