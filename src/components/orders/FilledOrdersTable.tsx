import { Badge } from '@/components/ui/badge'
import { pnlClass } from '@/lib/utils'
import { contractTerms, formatPrice } from './OrdersTable'
import type { FilledOrder } from '@/types'

const HEADERS = ['Time (ET)', 'Instrument', 'Type', 'Side', 'Qty', 'Avg price', 'Venue', 'Commission', 'Realized P&L']

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function FilledOrdersTable({ orders }: { orders: FilledOrder[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            {HEADERS.map((header) => (
              <th key={header} className="whitespace-nowrap px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.perm_id} className="border-b border-border last:border-0">
              <td className="whitespace-nowrap px-4 py-2.5 tabular-nums text-muted-foreground">{fmtTime(order.time)}</td>
              <td className="whitespace-nowrap px-4 py-2.5">
                <span className="font-mono font-semibold">{order.symbol}</span>
                <span className="ml-2 text-muted-foreground">{contractTerms(order)}</span>
              </td>
              <td className="px-4 py-2.5">
                <Badge variant="secondary" className="text-[10px]">
                  {order.asset_class}
                </Badge>
              </td>
              <td className="px-4 py-2.5 font-medium">{order.action}</td>
              <td className="px-4 py-2.5 tabular-nums">{order.quantity.toLocaleString()}</td>
              <td className="px-4 py-2.5 tabular-nums">{formatPrice(order.average_price, order.currency)}</td>
              <td className="px-4 py-2.5">{order.venue}</td>
              <td className="px-4 py-2.5 tabular-nums">{order.commission === null ? '' : formatPrice(order.commission, order.currency)}</td>
              <td className={`px-4 py-2.5 tabular-nums ${order.realized_pnl === null ? '' : pnlClass(order.realized_pnl)}`}>
                {order.realized_pnl === null ? '' : formatPrice(order.realized_pnl, order.currency)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
