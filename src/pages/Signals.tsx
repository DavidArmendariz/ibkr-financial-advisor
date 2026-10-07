import { ScrollArea } from '@/components/ui/scroll-area'
import { LiveValues } from '@/components/signals/LiveValues'
import { SignalSettingsForm } from '@/components/signals/SignalSettingsForm'
import { SignalStatusCards } from '@/components/signals/SignalStatusCards'
import { SignalTable } from '@/components/signals/SignalTable'
import { useSignals } from '@/hooks/useSignals'

export function SignalsPage() {
  const { status, live, history, settings, socketOpen, saveSettings } = useSignals()
  const symbol = status?.symbol ?? settings?.symbol ?? 'SOXL'

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h1 className="text-lg font-semibold">Signals</h1>
          <p className="text-sm text-muted-foreground">
            Real-time {symbol} entry alerts from deterministic rules, optionally filtered by your AI provider. Alerts
            only: no orders are placed.
          </p>
        </div>

        <SignalStatusCards status={status} socketOpen={socketOpen} />
        <LiveValues live={live} settings={settings} symbol={symbol} />

        <div>
          <h2 className="mb-2 text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Recent signals
          </h2>
          <SignalTable signals={history} />
        </div>

        {settings && <SignalSettingsForm settings={settings} onSave={saveSettings} />}
      </div>
    </ScrollArea>
  )
}
