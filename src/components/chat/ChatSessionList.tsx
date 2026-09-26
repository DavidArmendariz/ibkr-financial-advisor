import { MessageSquarePlus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import type { ChatThread } from '@/types'

interface Props {
  threads: ChatThread[]
  activeThreadId: string | null
  loading: boolean
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffDays = Math.floor(diffMs / 86_400_000)
  if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return d.toLocaleDateString([], { weekday: 'short' })
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export function ChatSessionList({ threads, activeThreadId, loading, onSelect, onCreate, onDelete }: Props) {
  return (
    <div className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-sidebar">
      {/* Header */}
      <div className="flex h-12 items-center justify-between px-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Conversations
        </span>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onCreate} title="New chat">
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>

      <Separator />

      {/* Thread list */}
      <ScrollArea className="flex-1">
        {loading && threads.length === 0 && (
          <div className="px-3 py-4 text-xs text-muted-foreground">Loading…</div>
        )}
        {!loading && threads.length === 0 && (
          <div className="px-3 py-4 text-xs text-muted-foreground">
            No conversations yet. Click + to start one.
          </div>
        )}
        <div className="flex flex-col gap-0.5 p-2">
          {threads.map((thread) => (
            <div
              key={thread.id}
              onClick={() => onSelect(thread.id)}
              className={cn(
                'group flex cursor-pointer items-start justify-between rounded-md px-3 py-2.5 text-sm transition-colors',
                activeThreadId === thread.id
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/40 hover:text-foreground',
              )}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm leading-tight">{thread.title}</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">
                  {formatDate(thread.updated_at)}
                </p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(thread.id) }}
                className="ml-2 shrink-0 rounded p-0.5 opacity-0 transition-opacity hover:bg-destructive/20 hover:text-destructive group-hover:opacity-100"
                title="Delete"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
