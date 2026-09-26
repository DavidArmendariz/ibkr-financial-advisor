import { useChat } from '@/hooks/useChat'
import { ChatSessionList } from '@/components/chat/ChatSessionList'
import { ChatWindow } from '@/components/chat/ChatWindow'

export function ChatPage() {
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
      <ChatWindow
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
        onSend={sendMessage}
        hasThread={activeThreadId !== null}
      />
    </div>
  )
}
