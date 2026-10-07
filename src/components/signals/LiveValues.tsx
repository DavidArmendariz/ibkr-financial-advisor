import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fmtPrice, fmtRatio, fmtTimeET } from './format'
import type { SignalLive, SignalSettings } from '@/types'

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border px-3 py-2.5">
      <span className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="text-base font-semibold tabular-nums">{value}</span>
    </div>
  )
}

export function LiveValues({ live, settings, symbol }: { live: SignalLive | null; settings: SignalSettings | null; symbol: string }) {
  const i = live?.indicators
  const fast = settings?.ema_fast ?? 9
  const slow = settings?.ema_slow ?? 21
  const bb = settings ? `Bollinger ${settings.bb_period}, ${settings.bb_std}σ · ` : ''

  return (
    <Card>
      <CardHeader className="flex flex-row items-baseline justify-between pb-3">
        <CardTitle className="text-sm">{symbol} live</CardTitle>
        <span className="text-xs text-muted-foreground">
          {bb}Last bar {fmtTimeET(live?.bar_time)} ET · price {fmtTimeET(live?.last_price_time)} ET
        </span>
      </CardHeader>
      <CardContent className="grid grid-cols-4 gap-2 pt-0">
        <Tile label="Last price" value={fmtPrice(live?.last_price ?? live?.bar_close)} />
        <Tile label="VWAP" value={fmtPrice(i?.vwap)} />
        <Tile label={`EMA ${fast}`} value={fmtPrice(i?.ema_fast)} />
        <Tile label={`EMA ${slow}`} value={fmtPrice(i?.ema_slow)} />
        <Tile label="BB upper" value={fmtPrice(i?.bb_upper)} />
        <Tile label="BB middle" value={fmtPrice(i?.bb_mid)} />
        <Tile label="BB lower" value={fmtPrice(i?.bb_lower)} />
        <Tile label="Relative volume" value={fmtRatio(i?.rvol)} />
      </CardContent>
    </Card>
  )
}
