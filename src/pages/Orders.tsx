import { RefreshCw } from 'lucide-react'
import { FilledOrdersTable } from '@/components/orders/FilledOrdersTable'
import { OrdersTable } from '@/components/orders/OrdersTable'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useFilledOrders } from '@/hooks/useFilledOrders'
import { useOpenOrders } from '@/hooks/useOpenOrders'

export function OrdersPage() {
  const { orders, status, loading, refresh } = useOpenOrders()
  const filled = useFilledOrders()
  const refreshAll = () => {
    refresh()
    filled.refresh()
  }

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">Orders</h1>
            <p className="text-sm text-muted-foreground">Working and filled orders on this account, including those placed in TWS</p>
          </div>
          <Button variant="outline" size="sm" onClick={refreshAll} disabled={loading} className="no-drag gap-2">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">Open orders</h2>

        {status === 'refused' && (
          <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm">
            <p className="font-medium text-amber-400">Open orders could not be read</p>
            <p className="mt-1 text-muted-foreground">
              TWS refused the request or didn't answer in time. The Read-Only API setting in TWS can cause this. Turning it off lets this
              view work, but it also removes TWS's own block on order placement. This app never places orders. Automatic refresh is
              paused, so click Refresh to try again.
            </p>
          </div>
        )}
        {status === 'disconnected' && <p className="text-sm text-amber-400">Not connected to IBKR. This list may be out of date.</p>}
        {status === 'unreachable' && <p className="text-sm text-red-400">Backend unreachable. This list may be out of date.</p>}

        {status === 'loading' && <Placeholder text="Loading orders…" />}
        {status === 'ready' && orders.length === 0 && <Placeholder text="No open orders" />}
        {orders.length > 0 && <OrdersTable orders={orders} />}

        <div>
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">Filled orders</h2>
          <p className="text-xs text-muted-foreground">Saved on this computer once the app sees them, kept separately for live and paper</p>
        </div>
        {filled.status === 'refused' && <p className="text-sm text-amber-400">Filled orders could not be read. IBKR didn't answer in time.</p>}
        {filled.status === 'loading' && <Placeholder text="Loading fills…" />}
        {filled.status === 'ready' && filled.orders.length === 0 && <Placeholder text="No filled orders" />}
        {filled.orders.length > 0 && <FilledOrdersTable orders={filled.orders} />}
      </div>
    </ScrollArea>
  )
}

function Placeholder({ text }: { text: string }) {
  return <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">{text}</div>
}
