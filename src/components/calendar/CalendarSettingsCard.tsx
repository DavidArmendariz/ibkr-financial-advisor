import { useEffect, useState } from 'react'
import axios from 'axios'
import { CalendarDays, CheckCircle2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { SymbolChips } from '@/components/calendar/SymbolChips'
import { getCalendar, updateCalendarSettings, type CalendarSettingsUpdate } from '@/lib/api'
import type { CalendarSettings } from '@/types'

function keyPlaceholder(set: boolean, hint: string | null) {
  return set ? `Saved (${hint ?? 'hidden'}), leave blank to keep it` : 'Paste your free API key'
}

export function CalendarSettingsCard() {
  const [saved, setSaved] = useState<CalendarSettings | null>(null)
  const [fredKey, setFredKey] = useState('')
  const [finnhubKey, setFinnhubKey] = useState('')
  const [symbols, setSymbols] = useState<string[]>([])
  const [evening, setEvening] = useState(true)
  const [soon, setSoon] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedOk, setSavedOk] = useState(false)

  const load = (settings: CalendarSettings) => {
    setSaved(settings)
    setSymbols(settings.earnings_symbols)
    setEvening(settings.alert_evening_enabled)
    setSoon(settings.alert_soon_enabled)
  }

  useEffect(() => {
    getCalendar()
      .then((state) => load(state.settings))
      .catch(() => setError('Could not load calendar settings'))
  }, [])

  // Chips save as they change: a chip on screen must already be in the watchlist.
  const changeSymbols = async (next: string[]) => {
    const previous = symbols
    setSymbols(next)
    setSavedOk(false)
    setError(null)
    try {
      setSaved(await updateCalendarSettings({ earnings_symbols: next.join(',') }))
    } catch {
      setSymbols(previous)
      setError('Could not save the watchlist')
    }
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    const values: CalendarSettingsUpdate = { alert_evening_enabled: evening, alert_soon_enabled: soon }
    if (fredKey.trim()) values.fred_api_key = fredKey.trim()
    if (finnhubKey.trim()) values.finnhub_api_key = finnhubKey.trim()
    setSaving(true)
    setError(null)
    setSavedOk(false)
    try {
      load(await updateCalendarSettings(values))
      setFredKey('')
      setFinnhubKey('')
      setSavedOk(true)
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null
      setError(typeof detail === 'string' ? detail : 'Could not save settings')
    } finally {
      setSaving(false)
    }
  }

  const toggle = (checked: boolean, onChange: (value: boolean) => void, label: string) => (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={checked} onChange={(e) => {
          onChange(e.target.checked)
          setSavedOk(false)
        }} disabled={saving} className="h-4 w-4 accent-white" />
      {label}
    </label>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarDays className="h-4 w-4" />
          Calendar
        </CardTitle>
        <CardDescription>Keys stay in the backend. FRED and Finnhub receive only your key and public date, series or symbol requests. The FRED key also powers M2 Money Supply.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={save} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            FRED API key
            <Input type="password" autoComplete="off" value={fredKey} onChange={(e) => { setFredKey(e.target.value); setSavedOk(false) }} placeholder={keyPlaceholder(!!saved?.fred_key_set, saved?.fred_key_hint ?? null)} disabled={saving} />
          </label>
          <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            Finnhub API key
            <Input type="password" autoComplete="off" value={finnhubKey} onChange={(e) => { setFinnhubKey(e.target.value); setSavedOk(false) }} placeholder={keyPlaceholder(!!saved?.finnhub_key_set, saved?.finnhub_key_hint ?? null)} disabled={saving} />
          </label>
          <div className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            Earnings watchlist
            <SymbolChips symbols={symbols} onChange={changeSymbols} disabled={saving} />
          </div>
          {toggle(evening, setEvening, 'Alert the evening before')}
          {toggle(soon, setSoon, 'Alert 30 minutes before')}
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={saving || !saved} className="gap-2">
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
          {error && <p className="text-sm text-red-400">{error}</p>}
        </form>
      </CardContent>
    </Card>
  )
}
