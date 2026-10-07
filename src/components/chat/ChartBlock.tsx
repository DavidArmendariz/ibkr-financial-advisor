import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { cn } from '@/lib/utils'

// Categorical palette, dark steps, in fixed order. Validated against the
// assistant bubble surface (#141414): adjacent CVD ΔE >= 8.4, all >= 3:1.
const SERIES_COLORS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
const MAX_SLICES = 8
const MAX_SERIES = 4
const GRID = 'rgba(255,255,255,0.08)'
const AXIS_TEXT = '#898781'
const SURFACE = '#141414'

interface Slice {
  label: string
  value: number
}

interface Series {
  name: string
  values: number[]
}

type ChartSpec =
  | { type: 'allocation'; title?: string; unit?: string; data: Slice[] }
  | { type: 'bar'; title?: string; unit?: string; categories: string[]; series: Series[] }
  | { type: 'line'; title?: string; unit?: string; x: string[]; series: Series[] }

// The spec comes from model output, so validate its shape instead of trusting it.
export function parseChartSpec(source: string): ChartSpec | null {
  let raw: unknown
  try {
    raw = JSON.parse(source)
  } catch {
    return null
  }
  if (!raw || typeof raw !== 'object') return null
  const spec = raw as Record<string, unknown>
  const title = typeof spec.title === 'string' ? spec.title : undefined
  const unit = typeof spec.unit === 'string' ? spec.unit : undefined
  const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
  const isStrArr = (v: unknown): v is string[] => Array.isArray(v) && v.every((s) => typeof s === 'string')
  const seriesOf = (v: unknown, len: number): Series[] | null => {
    if (!Array.isArray(v) || v.length === 0) return null
    const out = v.map((s) =>
      s && typeof s.name === 'string' && Array.isArray(s.values) && s.values.length === len && s.values.every(isNum)
        ? { name: s.name, values: s.values as number[] }
        : null,
    )
    return out.every(Boolean) ? (out as Series[]).slice(0, MAX_SERIES) : null
  }

  if (spec.type === 'allocation' && Array.isArray(spec.data)) {
    const data = spec.data.filter((d) => d && typeof d.label === 'string' && isNum(d.value) && d.value > 0)
    return data.length ? { type: 'allocation', title, unit, data: data.map((d) => ({ label: d.label, value: d.value })) } : null
  }
  if (spec.type === 'bar' && isStrArr(spec.categories) && spec.categories.length) {
    const series = seriesOf(spec.series, spec.categories.length)
    return series ? { type: 'bar', title, unit, categories: spec.categories, series } : null
  }
  if (spec.type === 'line' && isStrArr(spec.x) && spec.x.length > 1) {
    const series = seriesOf(spec.series, spec.x.length)
    return series ? { type: 'line', title, unit, x: spec.x, series } : null
  }
  return null
}

function formatValue(value: number, unit?: string, compact = false): string {
  if (unit === '%') return `${Number(value.toFixed(1))}%`
  if (unit === '$') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: compact ? 'compact' : 'standard',
      maximumFractionDigits: compact ? 1 : 0,
    }).format(value)
  }
  const n = new Intl.NumberFormat('en-US', {
    notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: 2,
  }).format(value)
  return unit ? `${n} ${unit}` : n
}

// Past eight slices, fold the smallest into "Other" rather than inventing more hues.
function foldSlices(data: Slice[]): Slice[] {
  if (data.length <= MAX_SLICES) return data
  const sorted = [...data].sort((a, b) => b.value - a.value)
  const kept = sorted.slice(0, MAX_SLICES - 1)
  const other = sorted.slice(MAX_SLICES - 1).reduce((sum, d) => sum + d.value, 0)
  return [...kept, { label: 'Other', value: other }]
}

export function ChartBlock({ spec }: { spec: ChartSpec }) {
  const [showTable, setShowTable] = useState(false)

  return (
    <figure className="my-3 w-[560px] max-w-full rounded-lg border border-border p-3">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        {spec.title && <figcaption className="text-xs font-semibold text-foreground">{spec.title}</figcaption>}
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          className="ml-auto shrink-0 text-[11px] text-muted-foreground hover:text-foreground"
        >
          {showTable ? 'Show chart' : 'Show table'}
        </button>
      </div>
      {showTable ? <DataTable spec={spec} /> : <ChartBody spec={spec} />}
    </figure>
  )
}

function ChartBody({ spec }: { spec: ChartSpec }) {
  if (spec.type === 'allocation') return <AllocationBar data={foldSlices(spec.data)} unit={spec.unit} />

  const rows =
    spec.type === 'bar'
      ? spec.categories.map((c, i) => ({ key: c, ...Object.fromEntries(spec.series.map((s) => [s.name, s.values[i]])) }))
      : spec.x.map((x, i) => ({ key: x, ...Object.fromEntries(spec.series.map((s) => [s.name, s.values[i]])) }))
  const multi = spec.series.length > 1
  const axisProps = { stroke: AXIS_TEXT, fontSize: 11, tickLine: false }
  const tooltip = (
    <Tooltip
      cursor={spec.type === 'bar' ? { fill: 'rgba(255,255,255,0.04)' } : { stroke: GRID, strokeWidth: 1 }}
      contentStyle={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, fontSize: 12 }}
      labelStyle={{ color: AXIS_TEXT, marginBottom: 2 }}
      itemStyle={{ color: '#fafafa', padding: 0 }}
      formatter={(v) => formatValue(Number(v), spec.unit)}
    />
  )
  const legend = multi ? (
    <Legend
      verticalAlign="top"
      align="left"
      iconSize={10}
      wrapperStyle={{ paddingBottom: 12 }}
      formatter={(value) => <span className="text-[11px] text-muted-foreground">{value}</span>}
    />
  ) : null

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        {spec.type === 'bar' ? (
          <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2} barCategoryGap="25%">
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="key" {...axisProps} axisLine={{ stroke: GRID }} interval={0} />
            <YAxis {...axisProps} axisLine={false} width={56} tickFormatter={(v) => formatValue(v, spec.unit, true)} />
            {tooltip}
            {legend}
            {spec.series.map((s, i) => (
              <Bar
                key={s.name}
                dataKey={s.name}
                fill={SERIES_COLORS[i]}
                maxBarSize={24}
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        ) : (
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="key" {...axisProps} axisLine={{ stroke: GRID }} minTickGap={16} />
            <YAxis
              {...axisProps}
              axisLine={false}
              width={56}
              domain={['auto', 'auto']}
              tickFormatter={(v) => formatValue(v, spec.unit, true)}
            />
            {tooltip}
            {legend}
            {spec.series.map((s, i) => (
              <Line
                key={s.name}
                dataKey={s.name}
                stroke={SERIES_COLORS[i]}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                dot={false}
                activeDot={{ r: 4, stroke: SURFACE, strokeWidth: 2 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

// Part-to-whole as a single stacked bar: segments separated by a 2px surface
// gap, with a legend that carries each label and value (never color alone).
function AllocationBar({ data, unit }: { data: Slice[]; unit?: string }) {
  const [hovered, setHovered] = useState<number | null>(null)
  const total = data.reduce((sum, d) => sum + d.value, 0)

  return (
    <div>
      <div className="flex h-6 w-full gap-[2px]" role="img" aria-label="Allocation breakdown">
        {data.map((d, i) => (
          <div
            key={d.label}
            onPointerEnter={() => setHovered(i)}
            onPointerLeave={() => setHovered(null)}
            className={cn(
              'h-full min-w-[3px] transition-opacity first:rounded-l last:rounded-r',
              hovered !== null && hovered !== i && 'opacity-50',
            )}
            style={{ flexGrow: d.value, flexBasis: 0, background: SERIES_COLORS[i] }}
            title={`${d.label}: ${formatValue(d.value, unit)}`}
          />
        ))}
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
        {data.map((d, i) => (
          <li
            key={d.label}
            onPointerEnter={() => setHovered(i)}
            onPointerLeave={() => setHovered(null)}
            className="flex items-center gap-2 text-xs"
          >
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: SERIES_COLORS[i] }} />
            <span className="truncate text-muted-foreground">{d.label}</span>
            <span className="ml-auto font-medium tabular-nums text-foreground">
              {formatValue(d.value, unit)}
              {unit !== '%' && total > 0 && (
                <span className="ml-1 font-normal text-muted-foreground">{((d.value / total) * 100).toFixed(0)}%</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function DataTable({ spec }: { spec: ChartSpec }) {
  const header =
    spec.type === 'allocation' ? ['', 'Value'] : ['', ...spec.series.map((s) => s.name)]
  const rows: (string | number)[][] =
    spec.type === 'allocation'
      ? spec.data.map((d) => [d.label, d.value])
      : (spec.type === 'bar' ? spec.categories : spec.x).map((k, i) => [k, ...spec.series.map((s) => s.values[i])])

  return (
    <div className="max-h-[240px] overflow-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-muted-foreground">
            {header.map((h, i) => (
              <th key={i} className={cn('px-2 py-1 font-medium', i === 0 ? 'text-left' : 'text-right')}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className="border-t border-border">
              {row.map((cell, c) => (
                <td key={c} className={cn('px-2 py-1', c === 0 ? 'text-left text-muted-foreground' : 'text-right tabular-nums')}>
                  {c === 0 ? cell : formatValue(Number(cell), spec.unit)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
