import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Moon, ShieldAlert, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { errorMessage } from '@/hooks/useTrading'
import * as api from '@/lib/api'
import { cn } from '@/lib/utils'
import { OrderChart, type ChartLine } from './OrderChart'
import type { OHLCBar, OrderReview, OrderSpecView, PlannerSymbol, TradeBracket, TradeDirection, TradingSessionName, TradingState } from '@/types'

export interface Levels {
  entry: number
  stop: number
  target: number
}

export interface Figures {
  shares: number
  value: number
  risk: number
  reward: number
  rewardRisk: number
  stopPct: number
  targetPct: number
  problem: string | null
}

const money = (n: number) => `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const SESSION_LABEL: Record<TradingSessionName, string> = {
  pre: 'Pre-market', regular: 'Regular hours', after: 'After-hours', overnight: 'Overnight', closed: 'Closed',
}

export function figures(direction: TradeDirection, l: Levels, riskBudget: number | null): Figures {
  const long = direction === 'long'
  let problem: string | null = null
  if (long && l.stop >= l.entry) problem = 'For a long trade the stop must be below the entry.'
  else if (!long && l.stop <= l.entry) problem = 'For a short trade the stop must be above the entry.'
  else if (long && l.target <= l.entry) problem = 'For a long trade the take profit must be above the entry.'
  else if (!long && l.target >= l.entry) problem = 'For a short trade the take profit must be below the entry.'
  const perShare = Math.abs(l.entry - l.stop)
  const shares = riskBudget && perShare > 0 && !problem ? Math.floor(riskBudget / perShare + 1e-9) : 0
  if (!problem && riskBudget === null) problem = "The account's net liquidation value isn't available, so set a dollar risk instead."
  if (!problem && shares < 1) problem = 'The risk amount is smaller than one share’s distance to the stop.'
  return {
    shares,
    value: shares * l.entry,
    risk: shares * perShare,
    reward: shares * Math.abs(l.target - l.entry),
    rewardRisk: perShare > 0 ? Math.abs(l.target - l.entry) / perShare : 0,
    stopPct: (l.stop / l.entry - 1) * 100,
    targetPct: (l.target / l.entry - 1) * 100,
    problem,
  }
}

function describe(o: OrderSpecView) {
  const price = o.order_type === 'STP LMT' ? `stop ${o.stop_price?.toFixed(2)}, limit ${o.limit_price.toFixed(2)}` : `limit ${o.limit_price.toFixed(2)}`
  const venue = o.exchange === 'OVERNIGHT' ? 'overnight venue' : `SMART${o.outside_rth ? ', outside regular hours' : ''}`
  return `${o.action} ${o.quantity} ${o.order_type} · ${price} · ${venue} · ${o.tif}`
}

function ReviewPanel({ review, onConfirm, onClose, busy, error }: { review: OrderReview; onConfirm: () => void; onClose: () => void; busy: boolean; error: string | null }) {
  const live = review.mode === 'live'
  const [left, setLeft] = useState(() => Math.max(0, Math.round((new Date(review.expires_at).getTime() - Date.now()) / 1000)))
  useEffect(() => {
    const timer = setInterval(() => setLeft(Math.max(0, Math.round((new Date(review.expires_at).getTime() - Date.now()) / 1000))), 1000)
    return () => clearInterval(timer)
  }, [review.expires_at])

  return (
    <div
      role="dialog"
      aria-label="Order review"
      className={cn('flex flex-col gap-3 rounded-lg border p-4 text-sm', live ? 'border-red-500/70 bg-red-950/30' : 'border-border bg-muted/30')}
    >
      <div className="flex items-start justify-between gap-3">
        <p className={cn('font-semibold', live && 'text-red-300')}>
          {live ? 'LIVE' : 'PAPER'} account {review.account}
          {review.kind === 'place' && ` · ${review.plan.direction === 'long' ? 'Long' : 'Short'} ${review.plan.shares} ${review.plan.symbol} · ${SESSION_LABEL[review.session]}`}
        </p>
        <button type="button" onClick={onClose} aria-label="Close the review" className="no-drag text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>

      {review.kind === 'place' && (
        <>
          <div>
            <p className="text-xs text-muted-foreground">Sent now</p>
            <ul className="mt-1 flex flex-col gap-1 font-mono text-xs">
              {review.orders.map((o, i) => (
                <li key={i}>
                  <span className="text-muted-foreground">{o.role}</span> {describe(o)}
                </li>
              ))}
            </ul>
          </div>
          {review.after_fill.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground">Sent by the app once the entry fills</p>
              <ul className="mt-1 flex flex-col gap-1 font-mono text-xs">
                {review.after_fill.map((o, i) => (
                  <li key={i}>
                    <span className="text-muted-foreground">{o.role}</span> {describe(o)}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {review.watched_stop !== null && (
            <p className="flex items-start gap-1.5 text-xs text-amber-300">
              <Moon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                IBKR doesn't accept stop orders overnight, so the app watches the stop at {review.watched_stop.toFixed(2)} and, if the{' '}
                {review.plan.direction === 'long' ? 'bid falls to it, sells' : 'ask rises to it, buys'} with a limit {review.gap_cap_percent}% past the price.{' '}
                <strong>This stop only works while this app and TWS are running and connected.</strong> The stop-limit at IBKR takes over at 4:00 ET.
              </span>
            </p>
          )}
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4">
            <dt className="text-muted-foreground">Value</dt>
            <dd className="tabular-nums">{money(review.value)}</dd>
            <dt className="text-muted-foreground">At risk</dt>
            <dd className="tabular-nums">{money(review.risk)}</dd>
            <dt className="text-muted-foreground">To target</dt>
            <dd className="tabular-nums">{money(review.reward)}</dd>
            <dt className="text-muted-foreground">IBKR commission</dt>
            <dd className="tabular-nums">{review.what_if.available && review.what_if.commission != null ? money(review.what_if.commission) : '—'}</dd>
            <dt className="text-muted-foreground">Margin change</dt>
            <dd className="tabular-nums">{review.what_if.available && review.what_if.init_margin_change != null ? money(review.what_if.init_margin_change) : '—'}</dd>
          </dl>
          {review.what_if.note && <p className="text-xs text-muted-foreground">{review.what_if.note}</p>}
          {review.what_if.warning && <p className="text-xs text-amber-300">IBKR: {review.what_if.warning}</p>}
          <p className="text-xs text-muted-foreground">
            The stop is a stop-limit: if the price gaps more than {review.gap_cap_percent}% past it, it may not fill.
          </p>
        </>
      )}
      {review.kind === 'modify' && (
        <p>
          Move the {review.role === 'stop' ? 'stop' : 'take profit'} from {review.from.toFixed(2)} to <strong>{review.to.toFixed(2)}</strong>.
        </p>
      )}
      {review.kind === 'cancel' && (
        <>
          <p>Cancel every working order in this bracket.</p>
          {review.warning && (
            <p className="flex items-start gap-1.5 text-xs text-amber-300">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {review.warning}
            </p>
          )}
        </>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          size="sm"
          onClick={onConfirm}
          disabled={busy || left === 0}
          className={cn('no-drag', live && 'bg-red-600 text-white hover:bg-red-500')}
        >
          {busy ? 'Sending…' : review.kind === 'place' ? (live ? 'Place LIVE order' : 'Place paper order') : review.kind === 'modify' ? 'Confirm change' : 'Cancel bracket'}
        </Button>
        <Button size="sm" variant="outline" onClick={onClose} className="no-drag">
          Back
        </Button>
        <span className="text-xs text-muted-foreground">{left > 0 ? `Valid for ${left}s` : 'Expired. Review again.'}</span>
      </div>
    </div>
  )
}

function BracketRow({ b, onModify, onCancel }: { b: TradeBracket; onModify: (b: TradeBracket) => void; onCancel: (b: TradeBracket) => void }) {
  const active = b.state === 'working' || b.state === 'open'
  const gaps = b.watched_stop?.gaps.length ?? 0
  return (
    <li className="flex flex-col gap-1 border-b border-border py-2 text-xs last:border-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-medium">
          {b.direction === 'long' ? 'Long' : 'Short'} {b.shares} {b.symbol}
        </span>
        <span className="text-muted-foreground">
          entry {b.entry.toFixed(2)} · stop {b.stop.toFixed(2)} · target {b.target.toFixed(2)}
        </span>
        <span className={cn('rounded px-1.5 py-0.5', active ? 'bg-accent' : 'text-muted-foreground')}>{b.state}</span>
        {active && (
          <span className="ml-auto flex gap-2">
            <Button size="sm" variant="outline" className="no-drag h-7" onClick={() => onModify(b)}>
              Edit levels
            </Button>
            <Button size="sm" variant="outline" className="no-drag h-7" onClick={() => onCancel(b)}>
              Cancel
            </Button>
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-x-3 text-muted-foreground">
        {Object.entries(b.orders).map(([role, o]) => (
          <span key={role}>
            {role.replace('_', ' ')}: {o.status}
            {o.message ? ` (${o.message})` : ''}
          </span>
        ))}
      </div>
      {b.watched_stop && (
        <p className={cn('flex items-center gap-1.5', b.watched_stop.active ? 'text-amber-300' : 'text-muted-foreground')}>
          <Moon className="h-3.5 w-3.5" />
          {b.watched_stop.triggered_at
            ? `App-watched stop fired at ${new Date(b.watched_stop.triggered_at).toLocaleTimeString()}`
            : b.watched_stop.active
              ? `App-watched stop at ${b.watched_stop.level.toFixed(2)} overnight`
              : 'App-watched stop off'}
          {gaps > 0 && ` · not watched ${gaps} time${gaps === 1 ? '' : 's'} (last from ${new Date(b.watched_stop.gaps[gaps - 1][0]).toLocaleTimeString()})`}
        </p>
      )}
      {b.warning && (
        <p className="flex items-start gap-1.5 text-red-400">
          <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {b.warning}
        </p>
      )}
    </li>
  )
}

interface Props {
  symbol: PlannerSymbol
  direction: TradeDirection
  onDirection: (d: TradeDirection) => void
  levels: Levels | null
  onLevels: (l: Levels) => void
  fig: Figures | null
  bars: OHLCBar[]
  bid: number | null
  ask: number | null
  trading: TradingState | null
  onRefresh: () => void
  onOpenSettings: () => void
}

export function OrderEntry({ symbol, direction, onDirection, levels, onLevels, fig, bars, bid, ask, trading, onRefresh, onOpenSettings }: Props) {
  const [review, setReview] = useState<OrderReview | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [moving, setMoving] = useState<{ id: string; price: number } | null>(null)
  const [editing, setEditing] = useState<TradeBracket | null>(null)

  const working = useMemo(
    () => (trading?.brackets ?? []).filter((b) => b.symbol === symbol && (b.state === 'working' || b.state === 'open')),
    [trading, symbol],
  )
  const recent = useMemo(() => (trading?.brackets ?? []).filter((b) => b.symbol === symbol).slice(0, 8), [trading, symbol])

  const lines: ChartLine[] = useMemo(() => {
    const out: ChartLine[] = []
    if (levels) {
      out.push({ id: 'draft:entry', role: 'entry', price: levels.entry, label: 'Entry', draggable: true, working: false })
      out.push({ id: 'draft:stop', role: 'stop', price: levels.stop, label: 'Stop', draggable: true, working: false })
      out.push({ id: 'draft:target', role: 'target', price: levels.target, label: 'Target', draggable: true, working: false })
    }
    for (const b of working) {
      const price = (role: 'stop' | 'target') => (moving?.id === `${b.id}:${role}` ? moving.price : b[role])
      out.push({ id: `${b.id}:stop`, role: 'stop', price: price('stop'), label: `Stop ${b.shares}`, draggable: true, working: true })
      out.push({ id: `${b.id}:target`, role: 'target', price: price('target'), label: `Target ${b.shares}`, draggable: true, working: true })
      if (b.state === 'working') out.push({ id: `${b.id}:entry`, role: 'entry', price: b.entry, label: `Entry ${b.shares}`, draggable: false, working: true })
    }
    return out
  }, [levels, working, moving])

  const startReview = async (load: () => Promise<OrderReview>) => {
    setBusy(true)
    setError(null)
    setReviewError(null)
    try {
      setReview(await load())
    } catch (e) {
      setError(errorMessage(e, 'The review failed.'))
    } finally {
      setBusy(false)
    }
  }

  const drag = (id: string, price: number) => {
    const [owner, role] = id.split(':')
    if (owner === 'draft' && levels) onLevels({ ...levels, [role]: price })
    else setMoving({ id, price })
  }
  const dragEnd = (id: string, price: number) => {
    const [owner, role] = id.split(':')
    if (owner === 'draft') {
      if (levels) onLevels({ ...levels, [role]: price })
      return
    }
    setMoving(null)
    startReview(() => api.reviewModify(owner, role as 'stop' | 'target', price))
  }

  const confirm = async () => {
    if (!review) return
    setBusy(true)
    setReviewError(null)
    try {
      await api.confirmOrder(review.token)
      setReview(null)
      setEditing(null)
      onRefresh()
    } catch (e) {
      setReviewError(errorMessage(e, 'IBKR did not accept the order.'))
    } finally {
      setBusy(false)
    }
  }

  const liveBlocked = trading?.mode === 'live' && !trading.settings.live_enabled
  const cap = trading?.settings.max_order_value ?? null
  const overCap = !!fig && !fig.problem && cap !== null && fig.value > cap
  const session = trading?.session ?? 'closed'
  const field = (key: keyof Levels, label: string) => (
    <label className="flex flex-col gap-1 text-xs text-muted-foreground">
      <span>{label}</span>
      <Input
        type="number"
        step={0.01}
        value={levels ? levels[key] : ''}
        disabled={!levels}
        onChange={(e) => levels && !Number.isNaN(e.target.valueAsNumber) && onLevels({ ...levels, [key]: e.target.valueAsNumber })}
        className="w-28 tabular-nums"
      />
    </label>
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1" role="group" aria-label="Direction">
          {(['long', 'short'] as const).map((d) => (
            <Button key={d} size="sm" variant={direction === d ? 'default' : 'outline'} aria-pressed={direction === d} onClick={() => onDirection(d)} className="no-drag">
              {d === 'long' ? 'Long' : 'Short'}
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {trading?.mode ? `${trading.mode === 'live' ? 'LIVE' : 'Paper'} ${trading.account ?? ''}` : 'Not connected'} · {SESSION_LABEL[session]}
        </p>
      </div>

      <OrderChart bars={bars} bid={bid} ask={ask} lines={lines} onDrag={drag} onDragEnd={dragEnd} />
      <p className="text-xs text-muted-foreground">
        Drag the dashed lines to set the entry, stop, and take profit; the share count follows your risk setting. Solid lines are working orders: drag one to change it.
      </p>

      <div className="flex flex-wrap items-end gap-3">
        {field('entry', 'Entry')}
        {field('stop', 'Stop')}
        {field('target', 'Take profit')}
        <Button
          size="sm"
          className="no-drag"
          disabled={busy || !levels || !fig || !!fig.problem || overCap || liveBlocked || session === 'closed' || !trading?.connected}
          onClick={() => levels && fig && startReview(() => api.reviewOrder({ symbol, direction, shares: fig.shares, ...levels }))}
        >
          Review order
        </Button>
        {fig && !fig.problem && <span className="text-xs text-muted-foreground">{fig.shares.toLocaleString('en-US')} shares · {money(fig.value)}</span>}
      </div>
      {fig?.problem && <p className="text-xs text-amber-400">{fig.problem}</p>}
      {overCap && fig && cap !== null && (
        <p className="text-xs text-amber-400">
          This order's value, {money(fig.value)}, is above the per-order cap of {money(cap)}. Widen the stop or lower the risk, or raise the cap in{' '}
          <button type="button" onClick={onOpenSettings} className="no-drag underline">
            Settings
          </button>
          .
        </p>
      )}
      {liveBlocked && (
        <p className="text-xs text-amber-400">
          Live trading is off.{' '}
          <button type="button" onClick={onOpenSettings} className="no-drag underline">
            Switch it on in Settings
          </button>{' '}
          to place live orders.
        </p>
      )}
      {session === 'closed' && <p className="text-xs text-muted-foreground">The market is closed, including the overnight session.</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}
      {review && <ReviewPanel review={review} busy={busy} error={reviewError} onConfirm={confirm} onClose={() => setReview(null)} />}

      {editing && (
        <div className="flex flex-wrap items-end gap-3 rounded-md border border-border p-3">
          <EditField label="Stop" initial={editing.stop} onReview={(p) => startReview(() => api.reviewModify(editing.id, 'stop', p))} />
          <EditField label="Take profit" initial={editing.target} onReview={(p) => startReview(() => api.reviewModify(editing.id, 'target', p))} />
          <Button size="sm" variant="outline" className="no-drag" onClick={() => setEditing(null)}>
            Done
          </Button>
        </div>
      )}

      {recent.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Brackets placed from this app</p>
          <ul className="mt-1">
            {recent.map((b) => (
              <BracketRow key={b.id} b={b} onModify={setEditing} onCancel={(x) => startReview(() => api.reviewCancel(x.id))} />
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function EditField({ label, initial, onReview }: { label: string; initial: number; onReview: (price: number) => void }) {
  const [value, setValue] = useState<number | ''>(initial)
  return (
    <label className="flex items-end gap-2 text-xs text-muted-foreground">
      <span className="flex flex-col gap-1">
        {label}
        <Input type="number" step={0.01} value={value} onChange={(e) => setValue(Number.isNaN(e.target.valueAsNumber) ? '' : e.target.valueAsNumber)} className="w-28 tabular-nums" />
      </span>
      <Button size="sm" variant="outline" className="no-drag" disabled={value === '' || value === initial} onClick={() => value !== '' && onReview(value)}>
        Review
      </Button>
    </label>
  )
}
