import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { AccountSummary } from '@/components/dashboard/AccountSummary'
import { PositionsTable } from '@/components/dashboard/PositionsTable'
import { TradingChart } from '@/components/dashboard/TradingChart'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { AccountSummary as AccountSummaryType, Position } from '@/types'

interface Props {
  summary: AccountSummaryType | null
  positions: Position[]
  loading: boolean
  onRefresh: () => void
}

export function Dashboard({ summary, positions, loading, onRefresh }: Props) {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">Portfolio Dashboard</h1>
            <p className="text-sm text-muted-foreground">Live data from Interactive Brokers</p>
          </div>
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Account Summary Cards */}
        <AccountSummary summary={summary} loading={loading} />

        {/* Positions Table */}
        <div>
          <h2 className="mb-2 text-sm font-medium text-muted-foreground uppercase tracking-wider">
            Open Positions
          </h2>
          <PositionsTable
            positions={positions}
            loading={loading}
            onRowClick={setSelectedSymbol}
          />
        </div>

        {/* Chart */}
        <TradingChart symbol={selectedSymbol} />
      </div>
    </ScrollArea>
  )
}
