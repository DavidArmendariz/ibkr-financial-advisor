import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn, formatCurrency, pnlClass } from '@/lib/utils'
import type { Position } from '@/types'

const col = createColumnHelper<Position>()

const columns = [
  col.accessor('symbol', {
    header: 'Ticker',
    cell: (info) => <span className="font-mono font-semibold">{info.getValue()}</span>,
  }),
  col.accessor('asset_class', {
    header: 'Type',
    cell: (info) => (
      <Badge variant="secondary" className="text-[10px]">
        {info.getValue()}
      </Badge>
    ),
  }),
  col.accessor('quantity', {
    header: 'Qty',
    cell: (info) => (
      <span className="tabular-nums">{info.getValue().toLocaleString()}</span>
    ),
  }),
  col.accessor('avg_cost', {
    header: 'Avg Cost',
    cell: (info) => <span className="tabular-nums">{formatCurrency(info.getValue())}</span>,
  }),
  col.accessor('market_price', {
    header: 'Mkt Price',
    cell: (info) => <span className="tabular-nums">{formatCurrency(info.getValue())}</span>,
  }),
  col.accessor('market_value', {
    header: 'Mkt Value',
    cell: (info) => <span className="tabular-nums">{formatCurrency(info.getValue())}</span>,
  }),
  col.accessor('unrealized_pnl', {
    header: 'Unreal. P&L',
    cell: (info) => {
      const v = info.getValue()
      return (
        <span className={cn('tabular-nums font-medium', pnlClass(v))}>
          {v >= 0 ? '+' : ''}
          {formatCurrency(v)}
        </span>
      )
    },
  }),
]

interface Props {
  positions: Position[]
  loading: boolean
  onRowClick?: (symbol: string) => void
}

export function PositionsTable({ positions, loading, onRowClick }: Props) {
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data: positions,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (loading && positions.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        Loading positions…
      </div>
    )
  }

  if (!loading && positions.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        No open positions
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border bg-muted/40">
              {hg.headers.map((header) => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  className={cn(
                    'px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground',
                    header.column.getCanSort() && 'cursor-pointer select-none hover:text-foreground',
                  )}
                >
                  <span className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getCanSort() && (
                      <span className="text-muted-foreground/50">
                        {header.column.getIsSorted() === 'asc' ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : header.column.getIsSorted() === 'desc' ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronsUpDown className="h-3 w-3" />
                        )}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row.original.symbol)}
              className={cn(
                'border-b border-border/50 transition-colors last:border-0',
                onRowClick && 'cursor-pointer hover:bg-accent/30',
              )}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
