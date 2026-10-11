import { useEffect, useState } from 'react'
import axios from 'axios'
import { CheckCircle2, Loader2, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { GammaSettings } from '@/types'

type Key = 'max_days' | 'strike_range_pct' | 'refresh_minutes' | 'risk_free_rate'

const FIELDS: { key: Key; label: string; step: number; scale?: number }[] = [
  { key: 'max_days', label: 'Expirations within (days)', step: 1 },
  { key: 'strike_range_pct', label: 'Strikes within ± (%)', step: 1 },
  { key: 'refresh_minutes', label: 'Refresh every (min)', step: 1 },
  { key: 'risk_free_rate', label: 'Risk-free rate (%)', step: 0.1, scale: 100 },
]

export function GammaSettingsForm({
  settings,
  onSave,
}: {
  settings: GammaSettings
  onSave: (values: Partial<GammaSettings>) => Promise<GammaSettings>
}) {
  const [draft, setDraft] = useState(settings)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedOk, setSavedOk] = useState(false)

  useEffect(() => setDraft(settings), [settings])

  const changes = Object.fromEntries(
    FIELDS.filter(({ key }) => draft[key] !== settings[key]).map(({ key }) => [key, draft[key]]),
  ) as Partial<GammaSettings>
  const dirty = Object.keys(changes).length > 0

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (Object.values(changes).some((v) => typeof v === 'number' && Number.isNaN(v))) {
      setError('Fill in every field')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSave(changes)
      setSavedOk(true)
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null
      setError(typeof detail === 'string' ? detail : 'Could not save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <SlidersHorizontal className="h-4 w-4" />
          Gamma settings
        </CardTitle>
        <CardDescription>Saving starts a new calculation. Wider ranges fetch more contracts and take longer.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-4 gap-3">
            {FIELDS.map(({ key, label, step, scale = 1 }) => (
              <label key={key} className="flex flex-col gap-1.5 text-xs text-muted-foreground">
                {label}
                <Input
                  type="number"
                  step={step}
                  value={Number.isNaN(draft[key]) ? '' : Number((draft[key] * scale).toFixed(4))}
                  onChange={(e) => {
                    setDraft((d) => ({ ...d, [key]: e.target.valueAsNumber / scale }))
                    setSavedOk(false)
                    setError(null)
                  }}
                  disabled={saving}
                  className="tabular-nums"
                />
              </label>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={!dirty || saving} className="gap-2">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
            {savedOk && !dirty && (
              <span className="flex items-center gap-1.5 text-sm text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                Saved
              </span>
            )}
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
        </form>
      </CardContent>
    </Card>
  )
}
