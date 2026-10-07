export const fmtPrice = (n: number | null | undefined) => (typeof n === 'number' ? n.toFixed(2) : '—')

export const fmtRatio = (n: number | null | undefined) => (typeof n === 'number' ? `${n.toFixed(2)}x` : '—')

export function fmtTimeET(iso: string | null | undefined, withDate = false): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const time = d.toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
  if (!withDate) return time
  const date = d.toLocaleDateString('en-US', { timeZone: 'America/New_York', month: 'short', day: 'numeric' })
  return `${date} ${time}`
}

export const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  openrouter: 'OpenRouter',
  local: 'Local model',
}
