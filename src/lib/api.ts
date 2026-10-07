import axios from 'axios'
import type {
  AccountSummary,
  AIProvider,
  AppSettings,
  ChatMessage,
  ChatThread,
  ConnectionStatus,
  OHLCBar,
  Position,
  SignalSettings,
  SignalState,
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

// ── Settings ─────────────────────────────────────────────────────────────────

export const getSettings = () =>
  http.get<AppSettings>('/api/settings').then((r) => r.data)

// Longer timeout: the backend verifies the key with Anthropic before saving it
export const saveAnthropicApiKey = (apiKey: string) =>
  http
    .put<AppSettings>('/api/settings/anthropic-api-key', { api_key: apiKey }, { timeout: 30_000 })
    .then((r) => r.data)

export const setAIProvider = (provider: AIProvider) =>
  http.put<AppSettings>('/api/settings/ai-provider', { provider }).then((r) => r.data)

// apiKey undefined keeps the saved key; '' clears it (local servers need none)
export const saveOpenAICompatible = (config: { baseUrl: string; model: string; apiKey?: string }) =>
  http
    .put<AppSettings>(
      '/api/settings/openai-compatible',
      { base_url: config.baseUrl, model: config.model, api_key: config.apiKey },
      { timeout: 30_000 },
    )
    .then((r) => r.data)

// ── WebSocket chat ────────────────────────────────────────────────────────────

export function createChatSocket(threadId: string): WebSocket {
  return new WebSocket(`ws://localhost:8000/api/chat/ws/${threadId}`)
}

// ── Signals ──────────────────────────────────────────────────────────────────

export const getSignalState = () => http.get<SignalState>('/api/signals/state').then((r) => r.data)

export const updateSignalSettings = (values: Partial<SignalSettings>) =>
  http.put<SignalSettings>('/api/signals/settings', values).then((r) => r.data)

export function createSignalsSocket(): WebSocket {
  return new WebSocket('ws://localhost:8000/api/signals/ws')
}
