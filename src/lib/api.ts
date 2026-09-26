import axios from 'axios'
import type {
  AccountSummary,
  ChatMessage,
  ChatThread,
  ConnectionStatus,
  OHLCBar,
  Position,
} from '@/types'

const BASE = 'http://localhost:8000'

const http = axios.create({ baseURL: BASE, timeout: 10_000 })

// ── Connection ──────────────────────────────────────────────────────────────

export const getConnectionStatus = () =>
  http.get<ConnectionStatus>('/api/connection/status').then((r) => r.data)

export const autoConnect = () =>
  http.post<ConnectionStatus>('/api/connection/auto-connect').then((r) => r.data)

export const connectTWS = (mode: 'paper' | 'live') =>
  http.post<ConnectionStatus>('/api/connection/connect', { mode }).then((r) => r.data)

export const disconnectTWS = () =>
  http.post('/api/connection/disconnect').then((r) => r.data)

// ── Portfolio ────────────────────────────────────────────────────────────────

export const getAccountSummary = () =>
  http.get<AccountSummary>('/api/portfolio/summary').then((r) => r.data)

export const getPositions = () =>
  http.get<Position[]>('/api/portfolio/positions').then((r) => r.data)

export const getPortfolioSnapshot = () =>
  http
    .get<{ summary: AccountSummary; positions: Position[] }>('/api/portfolio/snapshot')
    .then((r) => r.data)

export const getChartData = (
  symbol: string,
  duration = '1 D',
  barSize = '5 mins',
) =>
  http
    .get<OHLCBar[]>(`/api/portfolio/chart/${symbol}`, {
      params: { duration, bar_size: barSize },
    })
    .then((r) => r.data)

// ── Chat ─────────────────────────────────────────────────────────────────────

export const listThreads = () =>
  http.get<ChatThread[]>('/api/chat/threads').then((r) => r.data)

export const createThread = (title = 'New Chat') =>
  http.post<ChatThread>('/api/chat/threads', { title }).then((r) => r.data)

export const deleteThread = (threadId: string) =>
  http.delete(`/api/chat/threads/${threadId}`).then((r) => r.data)

export const getMessages = (threadId: string) =>
  http.get<ChatMessage[]>(`/api/chat/threads/${threadId}/messages`).then((r) => r.data)

// ── WebSocket chat ────────────────────────────────────────────────────────────

export function createChatSocket(threadId: string): WebSocket {
  return new WebSocket(`ws://localhost:8000/api/chat/ws/${threadId}`)
}
