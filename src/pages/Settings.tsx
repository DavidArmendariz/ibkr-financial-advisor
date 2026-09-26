import { useEffect, useState } from 'react'
import axios from 'axios'
import { Bot, CheckCircle2, KeyRound, Loader2, Server } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { getSettings, saveAnthropicApiKey, saveOpenAICompatible, setAIProvider } from '@/lib/api'
import type { AIProvider, AppSettings } from '@/types'

const PROVIDERS: { id: AIProvider; label: string; description: string }[] = [
  { id: 'anthropic', label: 'Anthropic', description: 'Claude, directly from Anthropic' },
  {
    id: 'openai_compatible',
    label: 'OpenAI-compatible',
    description: 'OpenRouter, OpenAI, or a local server (Ollama, LM Studio)',
  },
]

const PRESETS: { label: string; baseUrl: string; modelHint: string; local?: boolean }[] = [
  { label: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', modelHint: 'vendor/model-name' },
  { label: 'OpenAI', baseUrl: 'https://api.openai.com/v1', modelHint: 'model name' },
  { label: 'Ollama', baseUrl: 'http://localhost:11434/v1', modelHint: 'e.g. llama3.1', local: true },
  { label: 'LM Studio', baseUrl: 'http://localhost:1234/v1', modelHint: 'loaded model ID', local: true },
]

function errorDetail(err: unknown, fallback: string) {
  const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null
  return typeof detail === 'string' ? detail : fallback
}

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    getSettings().then(setSettings).catch(() => setLoadError('Could not load settings'))
  }, [])

  return (
    <ScrollArea className="h-full">
      <div className="flex max-w-2xl flex-col gap-4 p-6">
        <div>
          <h1 className="text-lg font-semibold">Settings</h1>
          <p className="text-sm text-muted-foreground">Stored locally on this machine</p>
        </div>

        {loadError && <p className="text-sm text-red-400">{loadError}</p>}
        {settings && (
          <>
            <ProviderCard settings={settings} onChange={setSettings} />
            {settings.ai_provider === 'anthropic' ? (
              <AnthropicCard settings={settings} onChange={setSettings} />
            ) : (
              <OpenAICompatCard settings={settings} onChange={setSettings} />
            )}
          </>
        )}
      </div>
    </ScrollArea>
  )
}

interface CardProps {
  settings: AppSettings
  onChange: (settings: AppSettings) => void
}

function ProviderCard({ settings, onChange }: CardProps) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const select = async (provider: AIProvider) => {
    if (provider === settings.ai_provider || saving) return
    setSaving(true)
    setError(null)
    try {
      onChange(await setAIProvider(provider))
    } catch (err) {
      setError(errorDetail(err, 'Failed to change the provider'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Bot className="h-4 w-4" />
          AI provider
        </CardTitle>
        <CardDescription>
          Which service answers in the AI Advisor. Your portfolio snapshot is sent to it with every
          message.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-2">
          {PROVIDERS.map(({ id, label, description }) => (
            <button
              key={id}
              onClick={() => select(id)}
              disabled={saving}
              className={cn(
                'rounded-lg border px-3 py-2.5 text-left transition-colors',
                settings.ai_provider === id
                  ? 'border-emerald-500/60 bg-emerald-500/10'
                  : 'border-border hover:bg-accent/50',
              )}
            >
              <p className="text-sm font-medium">{label}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
            </button>
          ))}
        </div>
        {!settings.ai_configured && (
          <p className="text-sm text-amber-400">
            This provider isn't set up yet. Configure it below.
          </p>
        )}
        {error && <p className="text-sm text-red-400">{error}</p>}
      </CardContent>
    </Card>
  )
}

function AnthropicCard({ settings, onChange }: CardProps) {
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim() || saving) return
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      onChange(await saveAnthropicApiKey(apiKey))
      setApiKey('')
      setSaved(true)
    } catch (err) {
      setError(errorDetail(err, 'Failed to save the API key'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="h-4 w-4" />
          Anthropic API key
        </CardTitle>
        <CardDescription>
          The key is verified with Anthropic, then saved to a local file readable only by your user
          account. It is never sent back to this window.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">
          {settings.anthropic_api_key_set ? (
            <span className="text-emerald-400">
              Key configured
              {settings.anthropic_api_key_hint && ` (${settings.anthropic_api_key_hint})`}
            </span>
          ) : (
            <span className="text-muted-foreground">No key configured</span>
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
            placeholder={settings.anthropic_api_key_set ? 'Enter a new key to replace it' : 'sk-ant-…'}
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
  )
}

function OpenAICompatCard({ settings, onChange }: CardProps) {
  const saved = settings.openai_compat
  const [baseUrl, setBaseUrl] = useState(saved.base_url)
  const [model, setModel] = useState(saved.model)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedOk, setSavedOk] = useState(false)

  const preset = PRESETS.find((p) => p.baseUrl === baseUrl.replace(/\/+$/, ''))

  const save = async (apiKeyValue: string | undefined) => {
    setSaving(true)
    setError(null)
    setSavedOk(false)
    try {
      onChange(await saveOpenAICompatible({ baseUrl, model, apiKey: apiKeyValue }))
      setApiKey('')
      setSavedOk(true)
    } catch (err) {
      setError(errorDetail(err, 'Failed to save the provider settings'))
    } finally {
      setSaving(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!baseUrl.trim() || !model.trim() || saving) return
    // A blank key field keeps the saved key
    save(apiKey.trim() ? apiKey : undefined)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Server className="h-4 w-4" />
          OpenAI-compatible provider
        </CardTitle>
        <CardDescription>
          Any service that speaks the OpenAI Chat Completions API. The URL and model are checked
          against the provider's model list before saving.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <Button
                key={p.label}
                type="button"
                size="sm"
                variant={preset?.label === p.label ? 'secondary' : 'outline'}
                onClick={() => {
                  setBaseUrl(p.baseUrl)
                  setSavedOk(false)
                }}
                disabled={saving}
              >
                {p.label}
              </Button>
            ))}
          </div>

          <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            Base URL
            <Input
              value={baseUrl}
              onChange={(e) => {
                setBaseUrl(e.target.value)
                setSavedOk(false)
              }}
              placeholder="https://…/v1"
              spellCheck={false}
              disabled={saving}
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            Model
            <Input
              value={model}
              onChange={(e) => {
                setModel(e.target.value)
                setSavedOk(false)
              }}
              placeholder={preset?.modelHint ?? 'model ID'}
              spellCheck={false}
              disabled={saving}
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            API key
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value)
                setSavedOk(false)
              }}
              placeholder={
                saved.api_key_set
                  ? `Saved (${saved.api_key_hint ?? 'hidden'}), leave blank to keep it`
                  : preset?.local
                    ? 'Not needed for local servers'
                    : 'API key'
              }
              autoComplete="off"
              spellCheck={false}
              disabled={saving}
            />
          </label>

          <div className="flex items-center gap-2">
            <Button
              type="submit"
              disabled={!baseUrl.trim() || !model.trim() || saving}
              className="gap-2"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving ? 'Verifying…' : 'Save'}
            </Button>
            {saved.api_key_set && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => save('')}
                disabled={!baseUrl.trim() || !model.trim() || saving}
              >
                Remove saved key
              </Button>
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}
          {savedOk && (
            <p className="flex items-center gap-1.5 text-sm text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              Provider verified and saved
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}
