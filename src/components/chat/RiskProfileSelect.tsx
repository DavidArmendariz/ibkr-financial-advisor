import { ChevronDown, Gauge } from 'lucide-react'
import type { RiskProfile } from '@/types'

const PROFILES: { id: RiskProfile; label: string; description: string }[] = [
  {
    id: 'conservative',
    label: 'Conservative',
    description: 'Capital preservation and income. Mostly bonds and cash, no margin.',
  },
  {
    id: 'moderate',
    label: 'Moderate',
    description: 'Balanced growth and stability. Diversified stocks and bonds.',
  },
  {
    id: 'aggressive',
    label: 'Aggressive',
    description: 'Maximum long-term growth. Mostly equities, accepts large drawdowns.',
  },
]

export function isRiskProfile(value: unknown): value is RiskProfile {
  return PROFILES.some((p) => p.id === value)
}

interface Props {
  value: RiskProfile
  onChange: (profile: RiskProfile) => void
  disabled?: boolean
}

export function RiskProfileSelect({ value, onChange, disabled }: Props) {
  const current = PROFILES.find((p) => p.id === value) ?? PROFILES[1]

  return (
    <div className="mb-2 flex items-center gap-2 text-xs">
      <Gauge className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <label htmlFor="risk-profile" className="shrink-0 text-muted-foreground">
        Risk profile
      </label>
      <div className="relative shrink-0">
        <select
          id="risk-profile"
          value={value}
          onChange={(e) => onChange(e.target.value as RiskProfile)}
          disabled={disabled}
          className="h-7 appearance-none rounded-md border border-border bg-secondary pl-2.5 pr-7 text-xs font-medium text-foreground outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
        >
          {PROFILES.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
      </div>
      <span className="truncate text-muted-foreground">{current.description}</span>
    </div>
  )
}
