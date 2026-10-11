import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ExpiryTable } from '@/components/gamma/ExpiryTable'
import { GammaByStrikeChart } from '@/components/gamma/GammaByStrikeChart'
import { GammaSettingsForm } from '@/components/gamma/GammaSettingsForm'
import { GammaSummary } from '@/components/gamma/GammaSummary'
import { fmtInt } from '@/components/gamma/format'
import { useGamma } from '@/hooks/useGamma'

function fmtUpdated(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function GammaPage() {
  const { state, unreachable, refresh, saveSettings } = useGamma()
  const result = state?.result ?? null
  const symbol = state?.settings.symbol ?? 'SOXL'
  const oi = result?.open_interest
  const covered = oi ? oi.live + oi.cached : 0
  const total = oi ? covered + oi.missing : 0
  const incomplete = oi !== undefined && total > 0 && oi.missing / total > 0.2

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold">Gamma exposure</h1>
            <p className="text-sm text-muted-foreground">
              Estimated dealer gamma in {symbol} options, from IBKR open interest and model greeks. Assumes dealers are long
              calls and short puts, so treat it as a rough map of hedging flows, not a forecast.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={refresh}
            disabled={!state || state.refreshing || !state.connected}
            className="shrink-0 gap-2"
          >
            {state?.refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {state?.refreshing && state.progress.total > 0
              ? `${fmtInt(state.progress.done)} / ${fmtInt(state.progress.total)} contracts`
              : state?.refreshing
                ? 'Loading chain…'
                : 'Refresh'}
          </Button>
        </div>

        {unreachable && <p className="text-sm text-red-400">Backend unreachable.</p>}
        {state?.error && <p className="text-sm text-red-400">{state.error}</p>}

        {result && (
          <>
            <p className="text-xs text-muted-foreground">
              Updated {fmtUpdated(result.updated_at)} ET · {fmtInt(result.contracts)} contracts with open interest ·{' '}
              {result.expirations.length} expirations ({result.expirations[0]} to {result.expirations.at(-1)}) · strikes $
              {result.strike_range[0].toFixed(0)}–${result.strike_range[1].toFixed(0)}
              {oi && oi.cached > 0 && oi.cached_as_of && <> · open interest saved {fmtUpdated(oi.cached_as_of)} ET</>}
            </p>
            {incomplete && (
              <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-400">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Open interest is available for only {fmtInt(covered)} of {fmtInt(total)} contracts, so these figures are
                  incomplete. IBKR reports open interest while the market is open; the first refresh during market hours
                  saves it for use after hours.
                </span>
              </div>
            )}
            <GammaSummary result={result} />
            <GammaByStrikeChart result={result} />
            <div>
              <h2 className="mb-2 text-sm font-medium uppercase tracking-wider text-muted-foreground">By expiration</h2>
              <ExpiryTable expiries={result.expiries} />
            </div>
          </>
        )}

        {!result && state && !state.refreshing && !state.error && (
          <div className="rounded-lg border border-border py-10 text-center text-sm text-muted-foreground">
            No calculation yet. {state.connected ? 'Click Refresh to start.' : 'Waiting for the IBKR connection.'}
          </div>
        )}

        {state && <GammaSettingsForm settings={state.settings} onSave={saveSettings} />}
      </div>
    </ScrollArea>
  )
}
