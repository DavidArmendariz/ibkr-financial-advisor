import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CONTRACTION_COLOR, GROWTH_COLOR, LEVEL_COLOR, fmtDollars, fmtMonth, fmtPct } from './format'
import type { MoneySupplyObservation } from '@/types'

const GRID = 'rgba(255,255,255,0.08)'
const AXIS = '#898781'
const SYNC = 'm2'

interface Row extends MoneySupplyObservation {
  growth: number | null
  contraction: number | null
}

// Growth and contraction are drawn as two areas so each gets its own colour. A segment that
// crosses zero needs its zero-side neighbour at 0, or the line would stop short of the axis.
function split(observations: MoneySupplyObservation[]): Row[] {
  return observations.map((o, i) => {
    const y = o.yoy_pct
    const near = (test: (v: number) => boolean) =>
      [observations[i - 1]?.yoy_pct, observations[i + 1]?.yoy_pct].some((v) => v != null && test(v))
    return {
      ...o,
      growth: y === null ? null : y >= 0 ? y : near((v) => v >= 0) ? 0 : null,
      contraction: y === null ? null : y < 0 ? y : near((v) => v < 0) ? 0 : null,
    }
  })
}

// January ticks on round years (every 1, 2, 5, 10 or 20), at most eight of them.
function yearTicks(rows: Row[]) {
  const januaries = rows.filter((r) => r.month.endsWith('-01-01')).map((r) => r.month)
  const step = [1, 2, 5, 10, 20].find((s) => januaries.length / s <= 8) ?? 20
  return januaries.filter((m) => Number(m.slice(0, 4)) % step === 0)
}

function MonthTooltip({ active, payload }: { active?: boolean; payload?: { payload: Row }[] }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-black/90 px-3 py-2 text-xs">
      <p className="mb-1 font-semibold">{fmtMonth(r.month)}</p>
      <p className="tabular-nums">
        <span className="font-semibold">{fmtDollars(r.value)}</span> <span className="text-muted-foreground">M2</span>
      </p>
      <p className="tabular-nums">
        <span className="font-semibold">{r.yoy_pct === null ? '—' : fmtPct(r.yoy_pct, 1)}</span>{' '}
        <span className="text-muted-foreground">vs. a year earlier</span>
      </p>
    </div>
  )
}

function Swatch({ color }: { color: string }) {
  return <span aria-hidden className="inline-block h-2 w-2 rounded-sm align-middle" style={{ backgroundColor: color }} />
}

const levelTick = (v: number) => `$${(v / 1000).toFixed(v % 1000 === 0 || v >= 10000 ? 0 : 1)}T`

export function M2Charts({ observations }: { observations: MoneySupplyObservation[] }) {
  const rows = split(observations)
  const ticks = yearTicks(rows)
  const xAxis = (
    <XAxis
      dataKey="month"
      ticks={ticks}
      tickFormatter={(m: string) => m.slice(0, 4)}
      stroke={AXIS}
      fontSize={11}
      tickLine={false}
      axisLine={{ stroke: GRID }}
      interval={0}
    />
  )
  const cursor = { stroke: 'rgba(255,255,255,0.35)', strokeWidth: 1 }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">M2 level</CardTitle>
        <p className="text-xs text-muted-foreground">Trillions of dollars, seasonally adjusted.</p>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <div className="h-[260px] w-full" role="img" aria-label="Line chart of the M2 money supply level">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} syncId={SYNC} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              {xAxis}
              <YAxis stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} width={56} tickFormatter={levelTick} domain={['auto', 'auto']} />
              <Tooltip cursor={cursor} content={<MonthTooltip />} />
              <Line dataKey="value" stroke={LEVEL_COLOR} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: '#1a1a19' }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold">Growth vs. a year earlier</p>
          <p className="text-xs text-muted-foreground">
            <Swatch color={GROWTH_COLOR} /> Growing <Swatch color={CONTRACTION_COLOR} /> Shrinking. Percent change from the same month a year before.
          </p>
        </div>
        <div className="h-[220px] w-full" role="img" aria-label="Area chart of M2 year-over-year growth">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={rows} syncId={SYNC} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              {xAxis}
              <YAxis stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} width={56} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip cursor={cursor} content={<MonthTooltip />} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.35)" />
              <Area dataKey="growth" baseValue={0} stroke={GROWTH_COLOR} strokeWidth={2} fill={GROWTH_COLOR} fillOpacity={0.15} connectNulls={false} dot={false} activeDot={false} isAnimationActive={false} />
              <Area dataKey="contraction" baseValue={0} stroke={CONTRACTION_COLOR} strokeWidth={2} fill={CONTRACTION_COLOR} fillOpacity={0.2} connectNulls={false} dot={false} activeDot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
