import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { CheckCircle2, Loader2, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { SignalSettings } from '@/types'

const TIMEFRAMES = [1, 2, 3, 5, 10, 15, 30]

type NumberKey = {
  [K in keyof SignalSettings]: SignalSettings[K] extends number ? K : never
}[keyof SignalSettings]
type TextKey = 'llm_model_anthropic' | 'llm_model_openai' | 'llm_model_openrouter'
type BoolKey = 'include_premarket' | 'llm_enabled'

interface Props {
  settings: SignalSettings
  onSave: (values: Partial<SignalSettings>) => Promise<SignalSettings>
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
      <span>
        {label}
        {hint && <span className="ml-1 opacity-70">({hint})</span>}
      </span>
      {children}
    </label>
  )
}

export function SignalSettingsForm({ settings, onSave }: Props) {
  const [draft, setDraft] = useState(settings)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedOk, setSavedOk] = useState(false)

  useEffect(() => setDraft(settings), [settings])

  const changes = useMemo(() => {
    const out: Partial<SignalSettings> = {}
    for (const key of Object.keys(settings) as (keyof SignalSettings)[]) {
      if (draft[key] !== settings[key]) (out as Record<string, unknown>)[key] = draft[key]
    }
    return out
  }, [draft, settings])
  const dirty = Object.keys(changes).length > 0

  const set = <K extends keyof SignalSettings>(key: K, value: SignalSettings[K]) => {
    setDraft((d) => ({ ...d, [key]: value }))
    setSavedOk(false)
    setError(null)
  }

  const num = (key: NumberKey, step = 1) => (
    <Input
      type="number"
      step={step}
      value={Number.isNaN(draft[key]) ? '' : draft[key]}
      onChange={(e) => set(key, e.target.valueAsNumber)}
      disabled={saving}
      className="tabular-nums"
    />
  )
  const text = (key: TextKey) => (
    <Input value={draft[key]} onChange={(e) => set(key, e.target.value)} spellCheck={false} disabled={saving} />
  )
  const check = (key: BoolKey, label: string) => (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={draft[key]}
        onChange={(e) => set(key, e.target.checked)}
        disabled={saving}
        className="h-4 w-4 accent-white"
      />
      {label}
    </label>
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (Object.values(changes).some((v) => typeof v === 'number' && Number.isNaN(v))) {
      setError('Fill in every number field')
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
          Signal settings
        </CardTitle>
        <CardDescription>
          Applied live. Changing the timeframe or an indicator period reloads history so the indicators restart cleanly.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <section className="flex flex-col gap-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Bars & indicators</h3>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Timeframe">
                <select
                  value={draft.timeframe_minutes}
                  onChange={(e) => set('timeframe_minutes', Number(e.target.value))}
                  disabled={saving}
                  className="h-9 rounded-md border border-input bg-transparent px-2 text-sm text-foreground"
                >
                  {TIMEFRAMES.map((m) => (
                    <option key={m} value={m}>
                      {m} min
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="EMA fast">{num('ema_fast')}</Field>
              <Field label="EMA slow">{num('ema_slow')}</Field>
              <Field label="Bollinger period">{num('bb_period')}</Field>
              <Field label="Bollinger width" hint="σ">{num('bb_std', 0.1)}</Field>
              <Field label="Relative volume lookback" hint="bars">{num('rvol_period')}</Field>
            </div>
            {check('include_premarket', 'Include pre-market in VWAP (session starts 04:00 ET instead of 09:30)')}
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Entry rule</h3>
            <div className="grid grid-cols-4 gap-3">
              <Field label="Min relative volume" hint="x">{num('rvol_threshold', 0.1)}</Field>
              <Field label="Cooldown" hint="min">{num('cooldown_minutes')}</Field>
              <Field label="Skip after open" hint="min">{num('open_blackout_minutes')}</Field>
              <Field label="Skip before close" hint="min">{num('close_blackout_minutes')}</Field>
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">LLM filter</h3>
            {check('llm_enabled', 'Filter each signal with the AI provider configured in Settings')}
            <div className="grid grid-cols-4 gap-3">
              <Field label="Min confidence" hint="0–1">{num('llm_confidence_threshold', 0.05)}</Field>
              <Field label="Anthropic model">{text('llm_model_anthropic')}</Field>
              <Field label="OpenAI model">{text('llm_model_openai')}</Field>
              <Field label="OpenRouter model">{text('llm_model_openrouter')}</Field>
            </div>
            <p className="text-xs text-muted-foreground">
              A local model (Ollama, LM Studio) uses the model set in Settings. Signals pass through unfiltered when the
              LLM times out (5 s), returns invalid JSON, or no provider is configured.
            </p>
          </section>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={!dirty || saving} className="gap-2">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
            {dirty && !saving && (
              <Button type="button" variant="ghost" onClick={() => setDraft(settings)}>
                Discard changes
              </Button>
            )}
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
