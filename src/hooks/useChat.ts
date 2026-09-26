import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '@/lib/api'
import type { ChatMessage, ChatThread } from '@/types'

export function useChat() {
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamingContent, setStreamingContent] = useState<string>('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [threadsLoading, setThreadsLoading] = useState(true)
  const wsRef = useRef<WebSocket | null>(null)

  // Load threads on mount
  const loadThreads = useCallback(async () => {
    setThreadsLoading(true)
    try {
      const data = await api.listThreads()
      setThreads(data)
    } finally {
      setThreadsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadThreads()
  }, [loadThreads])

  // Load messages when active thread changes
  const loadMessages = useCallback(async (threadId: string) => {
    const data = await api.getMessages(threadId)
    setMessages(data)
  }, [])

  useEffect(() => {
    if (!activeThreadId) {
      setMessages([])
      return
    }
    loadMessages(activeThreadId)
  }, [activeThreadId, loadMessages])

  const selectThread = useCallback(
    (threadId: string) => {
      wsRef.current?.close()
      wsRef.current = null
      setActiveThreadId(threadId)
      setStreamingContent('')
      setIsStreaming(false)
    },
    [],
  )

  const createThread = useCallback(async () => {
    const thread = await api.createThread()
    setThreads((prev) => [thread, ...prev])
    selectThread(thread.id)
    return thread
  }, [selectThread])

  const deleteThread = useCallback(
    async (threadId: string) => {
      await api.deleteThread(threadId)
      setThreads((prev) => prev.filter((t) => t.id !== threadId))
      if (activeThreadId === threadId) {
        setActiveThreadId(null)
        setMessages([])
      }
    },
    [activeThreadId],
  )

  const sendMessage = useCallback(
    async (text: string) => {
      if (!activeThreadId || isStreaming) return

      // Optimistically add user message to UI
      const optimistic: ChatMessage = {
        id: `tmp-${Date.now()}`,
        thread_id: activeThreadId,
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, optimistic])
      setStreamingContent('')
      setIsStreaming(true)

      // Open (or reuse) WebSocket connection
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        wsRef.current = api.createChatSocket(activeThreadId)
      }

      const ws = wsRef.current

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'chunk') {
          setStreamingContent((prev) => prev + data.content)
        } else if (data.type === 'done') {
          setIsStreaming(false)
          // Reload messages to get the persisted assistant message
          loadMessages(activeThreadId)
          setStreamingContent('')
          // Update thread timestamp in list
          loadThreads()
        } else if (data.type === 'error') {
          setIsStreaming(false)
          setStreamingContent('')
          console.error('Chat error:', data.content)
        }
      }

      ws.onerror = () => {
        setIsStreaming(false)
        setStreamingContent('')
      }

      const doSend = () => ws.send(JSON.stringify({ message: text }))
      if (ws.readyState === WebSocket.OPEN) {
        doSend()
      } else {
        ws.addEventListener('open', doSend, { once: true })
      }
    },
    [activeThreadId, isStreaming, loadMessages, loadThreads],
  )

  return {
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
  }
}
