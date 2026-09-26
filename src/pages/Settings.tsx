import { useEffect, useState } from 'react'
import axios from 'axios'
import { CheckCircle2, KeyRound, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { getSettings, saveAnthropicApiKey } from '@/lib/api'
import type { AppSettings } from '@/types'

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings().then(setSettings).catch(() => setError('Could not load settings'))
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim() || saving) return
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      setSettings(await saveAnthropicApiKey(apiKey))
      setApiKey('')
      setSaved(true)
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null
      setError(typeof detail === 'string' ? detail : 'Failed to save the API key')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ScrollArea className="h-full">
      <div className="flex max-w-2xl flex-col gap-4 p-6">
        <div>
          <h1 className="text-lg font-semibold">Settings</h1>
          <p className="text-sm text-muted-foreground">Stored locally on this machine</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <KeyRound className="h-4 w-4" />
              Anthropic API key
            </CardTitle>
            <CardDescription>
              Used by the AI Advisor. The key is verified with Anthropic, then saved to a local
              file readable only by your user account. It is never sent back to this window.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm">
              {settings === null ? (
                <span className="text-muted-foreground">Loading…</span>
              ) : settings.anthropic_api_key_set ? (
                <span className="text-emerald-400">
                  Key configured{settings.anthropic_api_key_hint && ` (${settings.anthropic_api_key_hint})`}
                </span>
              ) : (
                <span className="text-amber-400">No key configured</span>
              )}
            </p>

            <form onSubmit={handleSave} className="flex gap-2">
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  setSaved(false)
                }}
                placeholder={settings?.anthropic_api_key_set ? 'Enter a new key to replace it' : 'sk-ant-…'}
                autoComplete="off"
                spellCheck={false}
                disabled={saving}
              />
              <Button type="submit" disabled={!apiKey.trim() || saving} className="shrink-0 gap-2">
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {saving ? 'Verifying…' : 'Save'}
              </Button>
            </form>

            {error && <p className="text-sm text-red-400">{error}</p>}
            {saved && (
              <p className="flex items-center gap-1.5 text-sm text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                API key verified and saved
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}
