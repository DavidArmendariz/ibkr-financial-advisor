import { useEffect, useState } from 'react'
import { CheckCircle2, Loader2, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { errorMessage } from '@/hooks/useTrading'
import * as api from '@/lib/api'
import type { TradingSettings } from '@/types'

export function TradingSettingsCard() {
  const [saved, setSaved] = useState<TradingSettings | null>(null)
  const [draft, setDraft] = useState<TradingSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getTradingState()
      .then((s) => {
        setSaved(s.settings)
        setDraft(s.settings)
      })
      .catch(() => setError('Could not load trading settings'))
  }, [])

  const set = (values: Partial<TradingSettings>) => {
    setDraft((d) => (d ? { ...d, ...values } : d))
    setSavedOk(false)
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!draft || !saved) return
    const changes = Object.fromEntries(Object.entries(draft).filter(([k, v]) => saved[k as keyof TradingSettings] !== v))
    if (Object.keys(changes).length === 0) return
    setSaving(true)
    setError(null)
    try {
      const next = await api.updateTradingSettings(changes)
      setSaved(next)
      setDraft(next)
      setSavedOk(true)
    } catch (err) {
      setError(errorMessage(err, 'Could not save settings'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldAlert className="h-4 w-4" />
          Trading
        </CardTitle>
        <CardDescription>
          Orders are placed from the Trade Planner only, after you confirm a review. Paper orders are always allowed; live orders need the switch below.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {draft && (
          <form onSubmit={save} className="flex flex-col gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={draft.live_enabled} onChange={(e) => set({ live_enabled: e.target.checked })} disabled={saving} className="h-4 w-4 accent-white" />
              Allow live orders
            </label>
            <p className="text-xs text-muted-foreground">
              Live orders also need <strong>Read-Only API</strong> turned off in your live TWS (Global Configuration → API → Settings). Keep TWS's order
              precautions on, and answer No if TWS asks to bypass them for API orders.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
                Largest order value, paper and live ($)
                <Input type="number" min={1} step={100} value={draft.max_order_value} onChange={(e) => set({ max_order_value: e.target.valueAsNumber })} disabled={saving} />
              </label>
              <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
                Stop gap cap (%)
                <Input type="number" min={0.1} max={10} step={0.1} value={draft.gap_cap_percent} onChange={(e) => set({ gap_cap_percent: e.target.valueAsNumber })} disabled={saving} />
              </label>
            </div>
            <p className="text-xs text-muted-foreground">
              The gap cap sets how far past the stop the exit limit sits: the stop-limit at IBKR, and the app-watched stop overnight.
            </p>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={saving} className="gap-2">
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Save
              </Button>
              {savedOk && (
                <span className="flex items-center gap-1.5 text-sm text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                  Saved
                </span>
              )}
            </div>
          </form>
        )}
        {error && <p className="text-sm text-red-400">{error}</p>}
      </CardContent>
    </Card>
  )
}
