import { fmtGex, fmtInt } from './format'
import type { GammaExpiry } from '@/types'

function daysUntil(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  const today = new Date()
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((Date.UTC(y, m - 1, d) - start) / 86_400_000)
}

export function ExpiryTable({ expiries }: { expiries: GammaExpiry[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th className="px-3 py-2 font-medium">Expiration</th>
            <th className="px-3 py-2 text-right font-medium">Days</th>
            <th className="px-3 py-2 text-right font-medium">Calls</th>
            <th className="px-3 py-2 text-right font-medium">Puts</th>
            <th className="px-3 py-2 text-right font-medium">Net</th>
            <th className="px-3 py-2 text-right font-medium">Call OI</th>
            <th className="px-3 py-2 text-right font-medium">Put OI</th>
          </tr>
        </thead>
        <tbody>
          {expiries.map((e) => (
            <tr key={e.expiry} className="border-b border-border last:border-0">
              <td className="px-3 py-2 tabular-nums">{e.expiry}</td>
              <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">{daysUntil(e.expiry)}</td>
              <td className="px-3 py-2 text-right tabular-nums">{fmtGex(e.call)}</td>
              <td className="px-3 py-2 text-right tabular-nums">{fmtGex(e.put)}</td>
              <td className="px-3 py-2 text-right font-medium tabular-nums">{fmtGex(e.net)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">{fmtInt(e.call_oi)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">{fmtInt(e.put_oi)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
