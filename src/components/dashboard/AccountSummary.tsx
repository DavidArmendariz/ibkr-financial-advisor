import { ArrowDownRight, ArrowUpRight, DollarSign, TrendingUp, Wallet, Zap } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn, formatCurrency, pnlClass } from '@/lib/utils'
import type { AccountSummary as AccountSummaryType } from '@/types'

interface Props {
  summary: AccountSummaryType | null
  loading: boolean
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  valueClass,
}: {
  title: string
  value: string
  subtitle?: string
  icon: React.ElementType
  valueClass?: string
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={cn('text-xl font-bold tabular-nums', valueClass)}>{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  )
}

export function AccountSummary({ summary, loading }: Props) {
  if (loading && !summary) {
    return (
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <div className="h-3 w-24 rounded bg-muted animate-pulse" />
            </CardHeader>
            <CardContent>
              <div className="h-6 w-32 rounded bg-muted animate-pulse" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const s = summary

  const cards = [
    {
      title: 'Net Liq. Value',
      value: s ? formatCurrency(s.NetLiquidation) : '—',
      icon: DollarSign,
      valueClass: '',
    },
    {
      title: 'Unrealized P&L',
      value: s ? formatCurrency(s.UnrealizedPnL) : '—',
      subtitle: s ? (s.UnrealizedPnL >= 0 ? 'Profit' : 'Loss') : undefined,
      icon: s && s.UnrealizedPnL >= 0 ? ArrowUpRight : ArrowDownRight,
      valueClass: s ? pnlClass(s.UnrealizedPnL) : '',
    },
    {
      title: 'Realized P&L',
      value: s ? formatCurrency(s.RealizedPnL) : '—',
      icon: TrendingUp,
      valueClass: s ? pnlClass(s.RealizedPnL) : '',
    },
    {
      title: 'Buying Power',
      value: s ? formatCurrency(s.BuyingPower, true) : '—',
      subtitle: s ? `Cash: ${formatCurrency(s.TotalCashValue, true)}` : undefined,
      icon: Wallet,
      valueClass: '',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {cards.map((card) => (
        <StatCard key={card.title} {...card} />
      ))}
    </div>
  )
}
