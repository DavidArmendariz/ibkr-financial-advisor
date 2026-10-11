import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { fmtGex, fmtStrike } from './format'
import type { GammaResult } from '@/types'

function Tile({ label, value, detail, valueClass }: { label: string; value: string; detail?: string; valueClass?: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1 p-4">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
        <span className={cn('text-xl font-semibold tabular-nums', valueClass)}>{value}</span>
        {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
      </CardContent>
    </Card>
  )
}

export function GammaSummary({ result }: { result: GammaResult }) {
  const positive = result.net_gex >= 0
  const pct = (level: number | null) =>
    level === null ? undefined : `${(((level - result.spot) / result.spot) * 100).toFixed(1)}% from spot`

  return (
    <div className="grid grid-cols-3 gap-3 xl:grid-cols-6">
      <Tile label={`${result.symbol} price`} value={`$${result.spot.toFixed(2)}`} />
      <Tile
        label="Net gamma exposure"
        value={fmtGex(result.net_gex)}
        detail={positive ? 'Positive gamma: hedging tends to dampen moves' : 'Negative gamma: hedging tends to amplify moves'}
        valueClass={positive ? 'text-emerald-400' : 'text-red-400'}
      />
      <Tile label="Zero gamma" value={result.zero_gamma === null ? 'None in range' : `$${fmtStrike(result.zero_gamma)}`} detail={pct(result.zero_gamma)} />
      <Tile label="Call wall" value={result.call_wall === null ? '—' : `$${fmtStrike(result.call_wall)}`} detail={pct(result.call_wall)} />
      <Tile label="Put wall" value={result.put_wall === null ? '—' : `$${fmtStrike(result.put_wall)}`} detail={pct(result.put_wall)} />
      <Tile label="Calls / puts" value={`${fmtGex(result.call_gex, false)} / ${fmtGex(result.put_gex, false)}`} detail="Gamma exposure per 1% move" />
    </div>
  )
}
