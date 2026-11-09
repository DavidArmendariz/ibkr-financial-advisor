import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Check, Copy, RotateCcw } from 'lucide-react'
import { AtrCard, money } from '@/components/planner/AtrCard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { usePlanner } from '@/hooks/usePlanner'
import { useTrading } from '@/hooks/useTrading'
import { OrderEntry, figures, type Levels } from '@/components/trading/OrderEntry'
import * as api from '@/lib/api'
import { cn } from '@/lib/utils'
import type { PlannerSettings, TradeDirection, TradePlan } from '@/types'

function Toggle<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-col gap-1.5 text-xs text-muted-foreground">
      <span>{label}</span>
      <div className="no-drag flex gap-1" role="group" aria-label={label}>
        {options.map((o) => (
          <Button key={o.value} size="sm" variant={value === o.value ? 'default' : 'outline'} aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
            {o.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

function NumberField({ label, value, onChange, step = 0.1, placeholder }: { label: string; value: number | ''; onChange: (v: number | '') => void; step?: number; placeholder?: string }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
      <span>{label}</span>
      <Input
        type="number"
        step={step}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(Number.isNaN(e.target.valueAsNumber) ? '' : e.target.valueAsNumber)}
        className="tabular-nums"
      />
    </label>
  )
}

function Row({ label, value, sub, className }: { label: string; value: string; sub?: string; className?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border py-1.5 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn('tabular-nums', className)}>
        {value}
        {sub && <span className="ml-1.5 text-xs text-muted-foreground">{sub}</span>}
      </span>
    </div>
  )
}

const signed = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(2)}%`

// The planner sizes a long trade; a short mirrors its distances above and below the entry.
function levelsFrom(plan: Extract<TradePlan, { ok: true }>, direction: TradeDirection): Levels {
  if (direction === 'long') return { entry: plan.entry, stop: plan.stop, target: plan.target }
  const r = (n: number) => Math.round(n * 100) / 100
  return { entry: plan.entry, stop: r(2 * plan.entry - plan.stop), target: r(2 * plan.entry - plan.target) }
}

export function TradePlannerPage({ onOpenSettings }: { onOpenSettings: () => void }) {
  const { state, unreachable } = usePlanner()
  const [direction, setDirection] = useState<TradeDirection>('long')
  const [levels, setLevels] = useState<Levels | null>(null)
  const [dragged, setDragged] = useState(false)
  const [draft, setDraft] = useState<PlannerSettings | null>(null)
  const [entry, setEntry] = useState<number | ''>('')
  const [plan, setPlan] = useState<TradePlan | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const saveTimer = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (state && !draft) setDraft(state.settings)
  }, [state, draft])

  const update = (values: Partial<PlannerSettings>) => {
    setDraft((d) => (d ? { ...d, ...values } : d))
    // Settings save on their own, so the next launch opens with the same plan.
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      const valid = Object.entries(values).every(([, v]) => typeof v !== 'number' || v > 0)
      if (!valid) return
      api.updatePlannerSettings(values).then(() => setSaveError(null)).catch(() => setSaveError('Settings could not be saved'))
    }, 600)
  }

  const quoteKey = JSON.stringify(state?.quotes ?? null) + JSON.stringify(state?.account ?? null)
  useEffect(() => {
    if (!draft) return
    const numbers = [draft.stop_multiple, draft.target_multiple, draft.risk_percent, draft.risk_dollars]
    if (numbers.some((n) => typeof n !== 'number' || Number.isNaN(n))) {
      setPlan({ ok: false, reason: 'Fill in every field.' })
      return
    }
    const timer = setTimeout(() => {
      api
        .calculatePlan({ ...draft, entry: entry === '' ? null : entry })
        .then(setPlan)
        .catch(() => setPlan({ ok: false, reason: 'The plan could not be calculated.' }))
    }, 250)
    return () => clearTimeout(timer)
  }, [draft, entry, quoteKey])

  const trading = useTrading(draft?.symbol ?? 'SOXL')

  useEffect(() => {
    if (plan?.ok && !dragged) setLevels(levelsFrom(plan, direction))
    if (plan && !plan.ok && !dragged) setLevels(null)
  }, [plan, direction, dragged])

  if (!state || !draft) {
    return <div className="flex h-full items-center justify-center text-sm text-muted-foreground">{unreachable ? 'Backend unreachable' : 'Loading…'}</div>
  }

  const quote = state.quotes.find((q) => q.symbol === draft.symbol)
  const netLiq = state.account?.net_liquidation ?? null
  const riskBudget = draft.risk_mode === 'dollars' ? draft.risk_dollars : netLiq ? (netLiq * draft.risk_percent) / 100 : null
  const fig = levels ? figures(direction, levels, riskBudget) : null
  const funds = state.account?.available_funds ?? null
  const intradayLabel = `${state.intraday_minutes}-min ATR ${state.intraday_period}`
  const dailyLabel = `Daily ATR ${state.daily_period}`
  const order = levels && fig && !fig.problem
    ? `${direction === 'long' ? 'BUY' : 'SELL SHORT'} ${fig.shares} ${draft.symbol} LMT ${levels.entry.toFixed(2)} | Stop ${levels.stop.toFixed(2)} | Take profit ${levels.target.toFixed(2)}`
    : null

  const copy = async () => {
    if (!order) return
    await navigator.clipboard.writeText(order)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-6 p-6">
        <div>
          <h1 className="text-lg font-semibold">Trade Planner</h1>
          <p className="text-sm text-muted-foreground">
            ATR-based stop, target, and size for SOXL or SOXS, long or short. Drag the levels on the chart, review the orders, and confirm to send
            them to IBKR.
          </p>
        </div>
        {unreachable && <p className="text-sm text-red-400">Backend unreachable. Showing the last values received.</p>}
        {!unreachable && !state.connected && <p className="text-sm text-amber-400">Not connected to IBKR. Showing the last values received.</p>}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {state.quotes.map((q) => (
            <AtrCard key={q.symbol} quote={q} intradayLabel={intradayLabel} dailyLabel={dailyLabel} />
          ))}
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Chart and order</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <OrderEntry
              symbol={draft.symbol}
              direction={direction}
              onDirection={(d) => {
                setDirection(d)
                setDragged(false)
              }}
              levels={levels}
              onLevels={(l) => {
                setLevels(l)
                setDragged(true)
              }}
              fig={fig}
              bars={trading.bars}
              bid={quote?.bid ?? null}
              ask={quote?.ask ?? null}
              trading={trading.state}
              onRefresh={trading.refresh}
              onOpenSettings={onOpenSettings}
            />
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Inputs</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 pt-0">
              <div className="flex flex-wrap gap-4">
                <Toggle label="Symbol" value={draft.symbol} options={[{ value: 'SOXL', label: 'SOXL' }, { value: 'SOXS', label: 'SOXS' }]} onChange={(symbol) => { setEntry(''); setDragged(false); update({ symbol }) }} />
                <Toggle label="ATR basis" value={draft.atr_basis} options={[{ value: 'intraday', label: intradayLabel }, { value: 'daily', label: dailyLabel }]} onChange={(atr_basis) => update({ atr_basis })} />
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <NumberField label="Entry" value={entry} onChange={setEntry} step={0.01} placeholder={quote?.ask ? `${quote.ask.toFixed(2)} (ask)` : quote?.price ? `${quote.price.toFixed(2)} (last)` : 'ask'} />
                <NumberField label="Stop (× ATR)" value={draft.stop_multiple} onChange={(v) => update({ stop_multiple: v as number })} />
                <NumberField label="Target (× ATR)" value={draft.target_multiple} onChange={(v) => update({ target_multiple: v as number })} />
              </div>
              <div className="flex flex-wrap items-end gap-3">
                <Toggle label="Risk" value={draft.risk_mode} options={[{ value: 'percent', label: '% of account' }, { value: 'dollars', label: 'Dollars' }]} onChange={(risk_mode) => update({ risk_mode })} />
                {draft.risk_mode === 'percent' ? (
                  <NumberField label="Percent of net liquidation" value={draft.risk_percent} onChange={(v) => update({ risk_percent: v as number })} />
                ) : (
                  <NumberField label="Dollars at risk" value={draft.risk_dollars} onChange={(v) => update({ risk_dollars: v as number })} step={50} />
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {state.mode ? `${state.mode === 'live' ? 'Live' : 'Paper'} account` : 'No account'} · net liquidation {money(state.account?.net_liquidation ?? null)} ·
                available funds {money(state.account?.available_funds ?? null)}
              </p>
              {saveError && <p className="text-xs text-red-400">{saveError}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Plan</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 pt-0 text-sm">
              {!plan && <p className="text-muted-foreground">Calculating…</p>}
              {plan && !plan.ok && <p className="text-muted-foreground">{plan.reason}</p>}
              {plan?.ok && levels && fig && (
                <>
                  <div>
                    <Row label="Entry" value={money(levels.entry)} />
                    <Row label="Stop loss" value={money(levels.stop)} sub={signed(fig.stopPct)} className="text-red-400" />
                    <Row label="Take profit" value={money(levels.target)} sub={signed(fig.targetPct)} className="text-emerald-400" />
                    <Row label="Shares" value={fig.problem ? '—' : fig.shares.toLocaleString('en-US')} />
                    <Row label="Position value" value={fig.problem ? '—' : money(fig.value)} />
                    <Row label="At risk" value={fig.problem ? '—' : money(fig.risk)} />
                    <Row label="To target" value={fig.problem ? '—' : money(fig.reward)} />
                    <Row label="Reward : risk" value={`${fig.rewardRisk.toFixed(2)} : 1`} />
                  </div>
                  {dragged && (
                    <Button size="sm" variant="outline" className="no-drag gap-2 self-start" onClick={() => setDragged(false)}>
                      <RotateCcw className="h-4 w-4" />
                      Reset to the ATR levels
                    </Button>
                  )}
                  {!fig.problem && funds !== null && fig.value > funds && (
                    <p className="flex items-start gap-1.5 text-xs text-amber-400">
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      <span>The position is larger than your available funds.</span>
                    </p>
                  )}
                  {order && (
                    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
                      <span className="text-xs text-muted-foreground">Bracket values, to enter in TWS by hand if you prefer</span>
                      <code className="break-words text-xs">{order}</code>
                      <Button size="sm" variant="outline" className="no-drag gap-2 self-start" onClick={copy}>
                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        {copied ? 'Copied' : 'Copy'}
                      </Button>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">A stop is a price level, not a guaranteed fill: the price can gap past it.</p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ScrollArea>
  )
}
