import axios from 'axios'
import type {
  AccountSummary,
  AIProvider,
  AppSettings,
  CalendarSettings,
  CalendarState,
  ChatMessage,
  ChatThread,
  ConnectionStatus,
  GammaSettings,
  GammaState,
  FundamentalsLookup,
  FundamentalsWriteUp,
  GlobalMarketsState,
  MacroState,
  PlannerSettings,
  OHLCBar,
  OrderReview,
  PlaceReview,
  TradeBracket,
  TradeDirection,
  TradingSettings,
  TradingState,
  PlannerState,
  RotationSettings,
  RotationState,
  TradePlan,
  OpenOrdersState,
  FilledOrdersState,
  Position,
  SignalAnalysis,
  SignalAnalysisKind,
  SignalHistoryPage,
  SignalOutcomeResults,
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

// ── Orders ───────────────────────────────────────────────────────────────────

export const getFilledOrders = () =>
  http.get<FilledOrdersState>('/api/orders/filled').then((r) => r.data)

export const getOpenOrders = () =>
  http.get<OpenOrdersState>('/api/orders/open').then((r) => r.data)

// ── Calendar ─────────────────────────────────────────────────────────────────

export const getCalendar = () => http.get<CalendarState>('/api/calendar').then((r) => r.data)

export interface CalendarSettingsUpdate {
  fred_api_key?: string
  finnhub_api_key?: string
  earnings_symbols?: string
  alert_evening_enabled?: boolean
  alert_soon_enabled?: boolean
}

export const updateCalendarSettings = (values: CalendarSettingsUpdate) =>
  http.put<CalendarSettings>('/api/calendar/settings', values).then((r) => r.data)

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

export const getSignalHistory = (type: string | null, before?: string) =>
  http
    .get<SignalHistoryPage>('/api/signals/history', { params: { type: type ?? undefined, before } })
    .then((r) => r.data)

// Longer timeout: the backend allows the AI provider up to 60 seconds.
export const getSignalOutcomes = () => http.get<SignalOutcomeResults>('/api/signals/outcomes').then((r) => r.data)

export const runSignalAnalysis = (signalId: string, kind: SignalAnalysisKind) =>
  http
    .post<SignalAnalysis>(`/api/signals/${encodeURIComponent(signalId)}/analysis/${kind}`, undefined, { timeout: 90_000 })
    .then((r) => r.data)

export const updateSignalSettings = (values: Partial<SignalSettings>) =>
  http.put<SignalSettings>('/api/signals/settings', values).then((r) => r.data)

export function createSignalsSocket(): WebSocket {
  return new WebSocket('ws://localhost:8000/api/signals/ws')
}

// ── Gamma exposure ───────────────────────────────────────────────────────────

export const getGammaState = () => http.get<GammaState>('/api/gamma/state').then((r) => r.data)

export const refreshGamma = () => http.post<GammaState>('/api/gamma/refresh').then((r) => r.data)

export const updateGammaSettings = (values: Partial<GammaSettings>) =>
  http.put<GammaSettings>('/api/gamma/settings', values).then((r) => r.data)

// ── Macro ────────────────────────────────────────────────────────────────────

export const getGlobalMarkets = () => http.get<GlobalMarketsState>('/api/global-markets').then((r) => r.data)

export const getRotation = () => http.get<RotationState>('/api/rotation').then((r) => r.data)

export const updateRotationSettings = (values: Partial<RotationSettings>) =>
  http.put<RotationSettings>('/api/rotation/settings', values).then((r) => r.data)

export const getFundamentals = (ticker: string, refresh = false) =>
  http
    .get<FundamentalsLookup>(`/api/fundamentals/${encodeURIComponent(ticker)}`, { params: refresh ? { refresh: true } : {}, timeout: 90_000 })
    .then((r) => r.data)

export const writeFundamentalsAnalysis = (ticker: string) =>
  http.post<FundamentalsWriteUp>(`/api/fundamentals/${encodeURIComponent(ticker)}/analysis`, null, { timeout: 120_000 }).then((r) => r.data)

export const getNewsArticle = (provider: string, articleId: string) =>
  http
    .get<{ text: string | null }>(`/api/fundamentals/article/${encodeURIComponent(provider)}/${encodeURIComponent(articleId)}`, { timeout: 30_000 })
    .then((r) => r.data)

export const getTradingState = () => http.get<TradingState>('/api/trading/state').then((r) => r.data)

export const getTradingBars = (symbol: string) =>
  http.get<{ symbol: string; bars: OHLCBar[] }>(`/api/trading/bars/${symbol}`, { timeout: 30_000 }).then((r) => r.data.bars)

export const reviewOrder = (plan: { symbol: string; direction: TradeDirection; shares: number; entry: number; stop: number; target: number }) =>
  http.post<PlaceReview>('/api/trading/review', plan, { timeout: 45_000 }).then((r) => r.data)

export const confirmOrder = (token: string) =>
  http.post<TradeBracket>('/api/trading/confirm', { token }, { timeout: 45_000 }).then((r) => r.data)

export const reviewModify = (bracketId: string, role: 'stop' | 'target', price: number) =>
  http.post<OrderReview>(`/api/trading/brackets/${bracketId}/review-modify`, { role, price }).then((r) => r.data)

export const reviewCancel = (bracketId: string) =>
  http.post<OrderReview>(`/api/trading/brackets/${bracketId}/review-cancel`).then((r) => r.data)

export const updateTradingSettings = (values: Partial<TradingSettings>) =>
  http.put<TradingSettings>('/api/trading/settings', values).then((r) => r.data)

export const getPlanner = () => http.get<PlannerState>('/api/planner', { timeout: 60_000 }).then((r) => r.data)

export const updatePlannerSettings = (values: Partial<PlannerSettings>) =>
  http.put<PlannerSettings>('/api/planner/settings', values).then((r) => r.data)

export const calculatePlan = (request: PlannerSettings & { entry: number | null }) =>
  http.post<TradePlan>('/api/planner/plan', request).then((r) => r.data)

export const getMacroState = () => http.get<MacroState>('/api/macro/state').then((r) => r.data)
