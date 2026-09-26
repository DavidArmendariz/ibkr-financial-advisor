import { useEffect, useState } from 'react'
import { KeyRound } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { Button } from '@/components/ui/button'
import { getSettings } from '@/lib/api'
import { ChatSessionList } from '@/components/chat/ChatSessionList'
import { ChatWindow } from '@/components/chat/ChatWindow'

interface Props {
  onOpenSettings: () => void
}

export function ChatPage({ onOpenSettings }: Props) {
  const [hasApiKey, setHasApiKey] = useState(true)

  useEffect(() => {
    getSettings()
      .then((s) => setHasApiKey(s.anthropic_api_key_set))
      .catch(() => {})
  }, [])

  const {
    threads,
    threadsLoading,
    activeThreadId,
    messages,
    streamingContent,
    isStreaming,
    selectThread,
    createThread,
    deleteThread,
    sendMessage,
  } = useChat()

  return (
    <div className="flex h-full overflow-hidden">
      <ChatSessionList
        threads={threads}
        activeThreadId={activeThreadId}
        loading={threadsLoading}
        onSelect={selectThread}
        onCreate={createThread}
        onDelete={deleteThread}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        {!hasApiKey && (
          <div className="flex items-center justify-between gap-3 border-b border-border bg-amber-500/10 px-4 py-2 text-sm">
            <span className="flex items-center gap-2 text-amber-400">
              <KeyRound className="h-4 w-4" />
              Add your Anthropic API key to use the AI Advisor.
            </span>
            <Button size="sm" variant="outline" onClick={onOpenSettings}>
              Open Settings
            </Button>
          </div>
        )}
        <ChatWindow
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
          onSend={sendMessage}
          hasThread={activeThreadId !== null}
        />
      </div>
    </div>
  )
}
