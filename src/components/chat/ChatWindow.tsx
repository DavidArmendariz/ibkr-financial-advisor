import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { MessageBubble, StreamingBubble } from './MessageBubble'
import { RiskProfileSelect } from './RiskProfileSelect'
import type { ChatMessage, RiskProfile } from '@/types'

interface Props {
  messages: ChatMessage[]
  streamingContent: string
  isStreaming: boolean
  onSend: (text: string) => void
  hasThread: boolean
  riskProfile: RiskProfile
  onRiskProfileChange: (profile: RiskProfile) => void
}

export function ChatWindow({
  messages,
  streamingContent,
  isStreaming,
  onSend,
  hasThread,
  riskProfile,
  onRiskProfileChange,
}: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    onSend(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!hasThread) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-muted-foreground">
        <div className="text-4xl">💬</div>
        <p className="text-sm">Select a conversation or create a new one</p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="py-4">
          {messages.length === 0 && !isStreaming && (
            <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
              <p className="text-2xl">📊</p>
              <p className="text-sm font-medium">AI Financial Advisor</p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Ask anything about your portfolio — risk exposure, rebalancing ideas, P&L analysis,
                or market outlook. Your live portfolio data is automatically included.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {isStreaming && <StreamingBubble content={streamingContent} />}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-border p-4">
        <RiskProfileSelect value={riskProfile} onChange={onRiskProfileChange} disabled={isStreaming} />
        <div className="flex items-end gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your portfolio…"
            className="min-h-[44px] max-h-32 flex-1 bg-secondary resize-none"
            rows={1}
            disabled={isStreaming}
          />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="h-[44px] w-[44px] shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
          Enter to send · Shift+Enter for new line · Portfolio context auto-injected
        </p>
      </div>
    </div>
  )
}
