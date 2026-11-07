import { Badge } from '@/components/ui/badge'
import type { OpenOrder } from '@/types'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// IBKR sends YYYYMMDD, or YYYYMM for some futures.
function formatExpiry(expiry: string) {
  const month = MONTHS[Number(expiry.slice(4, 6)) - 1] ?? expiry
  const day = expiry.slice(6, 8)
  return `${day ? `${Number(day)} ` : ''}${month} ${expiry.slice(0, 4)}`
}

export function contractTerms({ expiry, strike, right }: Pick<OpenOrder, 'expiry' | 'strike' | 'right'>) {
  return [expiry && formatExpiry(expiry), strike, right].filter(Boolean).join(' ')
}

export function formatPrice(price: number | null, currency: string) {
  if (price === null) return ''
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 4 }).format(price)
}

const HEADERS = ['Instrument', 'Type', 'Side', 'Order', 'Qty', 'Filled', 'Remaining', 'Limit', 'Stop', 'TIF', 'Status']

export function OrdersTable({ orders }: { orders: OpenOrder[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            {HEADERS.map((header) => (
              <th
                key={header}
                className="whitespace-nowrap px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.perm_id} className="border-b border-border last:border-0">
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
              <td className="px-4 py-2.5">{order.order_type}</td>
              <td className="px-4 py-2.5 tabular-nums">{order.quantity.toLocaleString()}</td>
              <td className="px-4 py-2.5 tabular-nums">{order.filled.toLocaleString()}</td>
              <td className="px-4 py-2.5 tabular-nums">{order.remaining.toLocaleString()}</td>
              <td className="px-4 py-2.5 tabular-nums">{formatPrice(order.limit_price, order.currency)}</td>
              <td className="px-4 py-2.5 tabular-nums">{formatPrice(order.stop_price, order.currency)}</td>
              <td className="px-4 py-2.5">{order.time_in_force}</td>
              <td className="px-4 py-2.5">{order.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
