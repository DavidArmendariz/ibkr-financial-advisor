import { BarChart2, Bot, Settings, TrendingUp } from 'lucide-react'
import { cn, formatCurrency, pnlClass } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'
import type { AccountSummary, AppTab, ConnectionStatus } from '@/types'

interface Props {
  activeTab: AppTab
  onTabChange: (tab: AppTab) => void
  connectionStatus: ConnectionStatus
  summary: AccountSummary | null
}

const TABS: { id: AppTab; label: string; icon: React.ElementType }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart2 },
  { id: 'chat', label: 'AI Advisor', icon: Bot },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export function Sidebar({ activeTab, onTabChange, connectionStatus, summary }: Props) {
  const nlv = summary?.NetLiquidation ?? null
  const unrealizedPnl = summary?.UnrealizedPnL ?? null

  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      {/* Logo / title — also serves as the drag region for window movement */}
      <div className="drag-region flex h-12 items-center gap-2 px-4">
        <TrendingUp className="no-drag h-5 w-5 text-emerald-400" />
        <span className="no-drag text-sm font-semibold tracking-tight">IBKR Advisor</span>
      </div>

      <Separator />

      {/* Navigation tabs */}
      <nav className="flex flex-col gap-1 p-2 flex-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors w-full text-left',
              activeTab === id
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </button>
        ))}
      </nav>

      <Separator />

      {/* Footer: connection status + NLV */}
      <div className="flex flex-col gap-2 p-3">
        {/* Connection indicator */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              connectionStatus.connected ? 'bg-emerald-400 shadow-[0_0_6px_1px_rgba(52,211,153,0.6)]' : 'bg-red-500',
            )}
          />
          {connectionStatus.connected
            ? `Connected · ${connectionStatus.mode === 'paper' ? 'Paper' : 'Live'}`
            : 'Disconnected'}
        </div>

        {/* Net Liquidation Value */}
        {nlv !== null && (
          <div className="rounded-md border border-border bg-card px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Net Liq. Value
            </p>
            <p className="mt-0.5 text-sm font-semibold tabular-nums">
              {formatCurrency(nlv)}
            </p>
            {unrealizedPnl !== null && (
              <p className={cn('text-xs tabular-nums', pnlClass(unrealizedPnl))}>
                {unrealizedPnl >= 0 ? '▲' : '▼'} {formatCurrency(Math.abs(unrealizedPnl))} unrealized
              </p>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
