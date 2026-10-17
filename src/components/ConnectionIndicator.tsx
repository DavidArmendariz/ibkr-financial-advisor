import { cn } from '@/lib/utils'
import type { ConnectionStatus } from '@/types'

export function ConnectionIndicator({ status, className }: { status: ConnectionStatus; className?: string }) {
  return (
    <div className={cn('flex items-center gap-2 text-xs text-muted-foreground', className)}>
      <span
        className={cn(
          'h-2 w-2 rounded-full',
          status.connected ? 'bg-emerald-400 shadow-[0_0_6px_1px_rgba(52,211,153,0.6)]' : 'bg-red-500',
        )}
      />
      {status.connected ? `Connected · ${status.mode === 'paper' ? 'Paper' : 'Live'}` : 'Disconnected'}
    </div>
  )
}
