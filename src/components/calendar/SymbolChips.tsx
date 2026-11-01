import { useState } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  symbols: string[]
  onChange: (symbols: string[]) => void
  disabled?: boolean
}

// Accepts several at once, so a pasted "NVDA, AMD" still becomes two chips.
export function parseSymbols(text: string) {
  return text
    .split(/[\s,;]+/)
    .map((s) => s.trim().toUpperCase())
    .filter((s) => /^[A-Z0-9.-]{1,10}$/.test(s))
}

export function SymbolChips({ symbols, onChange, disabled }: Props) {
  const [draft, setDraft] = useState('')

  const commit = (text: string) => {
    const added = parseSymbols(text).filter((s) => !symbols.includes(s))
    if (added.length > 0) onChange([...symbols, ...added])
    setDraft('')
  }

  return (
    <div
      className={cn(
        'flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-input bg-transparent px-2 py-1.5',
        'focus-within:ring-1 focus-within:ring-ring',
        disabled && 'opacity-50',
      )}
    >
      {symbols.map((symbol) => (
        <span key={symbol} className="inline-flex items-center gap-1 rounded bg-secondary py-0.5 pl-2 pr-1 font-mono text-xs text-secondary-foreground">
          {symbol}
          <button
            type="button"
            onClick={() => onChange(symbols.filter((s) => s !== symbol))}
            disabled={disabled}
            aria-label={`Remove ${symbol}`}
            className="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => {
          const text = e.target.value
          if (/[\s,;]/.test(text)) commit(text)
          else setDraft(text)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            // Enter adds a chip; it mustn't also submit the settings form.
            e.preventDefault()
            commit(draft)
          } else if (e.key === 'Backspace' && !draft && symbols.length > 0) {
            onChange(symbols.slice(0, -1))
          }
        }}
        onBlur={() => commit(draft)}
        disabled={disabled}
        spellCheck={false}
        aria-label="Add a ticker to the earnings watchlist"
        placeholder={symbols.length === 0 ? 'Add a ticker' : 'Add ticker'}
        className="min-w-20 flex-1 bg-transparent text-xs text-foreground uppercase outline-none placeholder:normal-case placeholder:text-muted-foreground"
      />
    </div>
  )
}
