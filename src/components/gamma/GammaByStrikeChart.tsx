import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CALL_COLOR, PUT_COLOR, fmtGex, fmtInt, fmtStrike } from './format'
import type { GammaResult, GammaStrike } from '@/types'

const GRID = 'rgba(255,255,255,0.08)'
const AXIS = '#898781'

function nearest(strikes: GammaStrike[], level: number | null) {
  if (level === null || strikes.length === 0) return null
  return strikes.reduce((a, b) => (Math.abs(b.strike - level) < Math.abs(a.strike - level) ? b : a)).strike
}

function StrikeTooltip({ active, payload }: { active?: boolean; payload?: { payload: GammaStrike }[] }) {
  if (!active || !payload?.length) return null
  const s = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-black/90 px-3 py-2 text-xs">
      <p className="mb-1 font-semibold">Strike ${fmtStrike(s.strike)}</p>
      <p className="tabular-nums">
        <span className="font-semibold">{fmtGex(s.net)}</span> <span className="text-muted-foreground">net</span>
      </p>
      <p className="tabular-nums text-muted-foreground">
        Calls {fmtGex(s.call)} · OI {fmtInt(s.call_oi)}
      </p>
      <p className="tabular-nums text-muted-foreground">
        Puts {fmtGex(s.put)} · OI {fmtInt(s.put_oi)}
      </p>
    </div>
  )
}

export function GammaByStrikeChart({ result }: { result: GammaResult }) {
  const data = result.strikes.filter((s) => s.call !== 0 || s.put !== 0)
  const spotStrike = nearest(data, result.spot)
  const flipStrike = nearest(data, result.zero_gamma)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Gamma exposure by strike</CardTitle>
        <p className="text-xs text-muted-foreground">
          Dollar gamma per 1% move in {result.symbol}, all expirations in range. Calls above zero, puts below.
        </p>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-xs text-muted-foreground">No exposure to show</div>
        ) : (
          <div className="h-[340px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} stackOffset="sign" margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barCategoryGap="15%">
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="strike" stroke={AXIS} fontSize={11} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={12} />
                <YAxis stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} width={64} tickFormatter={(v) => fmtGex(v)} />
                <Tooltip cursor={{ fill: 'rgba(255,255,255,0.04)' }} content={<StrikeTooltip />} />
                <Legend
                  verticalAlign="top"
                  align="left"
                  iconSize={10}
                  wrapperStyle={{ paddingBottom: 12 }}
                  formatter={(value) => <span className="text-[11px] text-muted-foreground">{value}</span>}
                />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.25)" />
                {spotStrike !== null && (
                  <ReferenceLine
                    x={spotStrike}
                    stroke="rgba(255,255,255,0.6)"
                    label={{ value: `Spot ${result.spot.toFixed(2)}`, position: 'top', fill: '#fafafa', fontSize: 11 }}
                  />
                )}
                {flipStrike !== null && flipStrike !== spotStrike && (
                  <ReferenceLine
                    x={flipStrike}
                    stroke="#c98500"
                    strokeDasharray="4 3"
                    label={{ value: 'Zero gamma', position: 'insideTopRight', fill: '#c98500', fontSize: 11 }}
                  />
                )}
                <Bar dataKey="call" name="Calls" stackId="gex" fill={CALL_COLOR} maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="put" name="Puts" stackId="gex" fill={PUT_COLOR} maxBarSize={24} radius={[0, 0, 4, 4]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
