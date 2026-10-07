import { useState } from 'react'
import { MessageSquarePlus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
  onDelete: (id: string) => Promise<void> | void
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
  // Deleting is permanent, so the trash button asks for confirmation in a modal.
  const [pendingDelete, setPendingDelete] = useState<ChatThread | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const closeDialog = () => {
    if (deleting) return
    setPendingDelete(null)
    setDeleteError(null)
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await onDelete(pendingDelete.id)
      setPendingDelete(null)
    } catch {
      setDeleteError('Could not delete the conversation. Try again.')
    } finally {
      setDeleting(false)
    }
  }

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
              title={thread.title}
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
                onClick={(e) => {
                  e.stopPropagation()
                  setPendingDelete(thread)
                }}
                className={cn(
                  'ml-2 shrink-0 rounded p-1 text-muted-foreground transition-opacity hover:bg-destructive/20 hover:text-red-400 focus-visible:opacity-100 group-hover:opacity-100',
                  activeThreadId === thread.id ? 'opacity-100' : 'opacity-0',
                )}
                title="Delete conversation"
                aria-label={`Delete conversation: ${thread.title}`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </ScrollArea>

      <Dialog open={pendingDelete !== null} onOpenChange={(open) => !open && closeDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete conversation?</DialogTitle>
            <DialogDescription>
              <span className="font-medium text-foreground">“{pendingDelete?.title}”</span> and all of its
              messages will be permanently deleted. This can't be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteError && <p className="text-sm text-red-400">{deleteError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting ? 'Deleting…' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
