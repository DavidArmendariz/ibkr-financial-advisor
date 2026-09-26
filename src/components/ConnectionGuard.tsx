import { AlertCircle, Loader2, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ConnectionStatus } from '@/types'

interface Props {
  status: ConnectionStatus
  loading: boolean
  error: string | null
  autoConnect: boolean
  onConnect: (mode?: 'paper' | 'live') => void
}

export function ConnectionGuard({ status, loading, error, autoConnect, onConnect }: Props) {
  return (
    <div className="flex h-screen flex-col items-center justify-center bg-background px-6 drag-region">
      <div className="no-drag flex w-full max-w-md flex-col items-center gap-8">
        {/* Icon */}
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl border border-border bg-card">
          {loading ? (
            <Loader2 className="h-9 w-9 animate-spin text-muted-foreground" />
          ) : status.connected ? (
            <Wifi className="h-9 w-9 text-emerald-400" />
          ) : (
            <WifiOff className="h-9 w-9 text-zinc-500" />
          )}
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">
            {loading ? 'Connecting…' : 'Connect to IBKR'}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {loading
              ? 'Searching for TWS / IB Gateway on localhost…'
              : 'TWS or IB Gateway must be running locally before you can continue.'}
          </p>
        </div>

        {/* Error */}
        {error && !loading && (
          <div className="flex w-full items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <span>{error}</span>
          </div>
        )}

        {/* Retry buttons */}
        {!loading && (
          <div className="flex w-full flex-col gap-2">
            <Button className="w-full" onClick={() => onConnect()} disabled={loading}>
              <RefreshCw className="h-4 w-4" />
              Auto-Connect (Paper / Live)
            </Button>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" onClick={() => onConnect('paper')} disabled={loading}>
                Paper (7497)
              </Button>
              <Button variant="outline" onClick={() => onConnect('live')} disabled={loading}>
                Live (7496)
              </Button>
            </div>
            {autoConnect && (
              <p className="text-center text-xs text-muted-foreground">
                Retrying automatically every 10 seconds
              </p>
            )}
          </div>
        )}

        {/* Instructions */}
        <div className="w-full rounded-lg border border-border bg-card px-4 py-4 text-xs text-muted-foreground space-y-1.5">
          <p className="font-medium text-foreground">Setup checklist</p>
          <ol className="list-decimal list-inside space-y-1">
            <li>Open Trader Workstation (TWS) or IB Gateway and log in (Paper Trading for testing)</li>
            <li>Go to <strong>File → Global Configuration → API → Settings</strong> and dismiss the API announcements pop-up</li>
            <li>Enable <strong>Enable ActiveX and Socket Clients</strong> (it's off by default)</li>
            <li>Set Socket port to <strong>7497</strong> (paper) or <strong>7496</strong> (live)</li>
            <li>Leave <strong>Read-Only API</strong> on; the app only reads data</li>
            <li>Click <strong>Apply</strong> → <strong>OK</strong>, then <strong>Accept</strong> the incoming API connection prompt</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
