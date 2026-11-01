export interface ConnectionStatus {
  connected: boolean
  port: number | null
  mode: 'paper' | 'live' | null
  server_version: string | null
}

export interface AccountSummary {
  NetLiquidation: number
  UnrealizedPnL: number
  RealizedPnL: number
  BuyingPower: number
  TotalCashValue: number
  GrossPositionValue: number
}

export interface Position {
  symbol: string
  asset_class: string
  currency: string
  quantity: number
  avg_cost: number
  market_price: number
  market_value: number
  unrealized_pnl: number
  realized_pnl: number
}

export interface OHLCBar {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface ChatThread {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  thread_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export type AIProvider = 'anthropic' | 'openai_compatible'

export interface AppSettings {
  ai_provider: AIProvider
  ai_configured: boolean
  anthropic_api_key_set: boolean
  anthropic_api_key_hint: string | null
  openai_compat: {
    base_url: string
    model: string
    api_key_set: boolean
    api_key_hint: string | null
  }
}

export interface OpenOrder {
  perm_id: number
  symbol: string
  asset_class: string
  currency: string
  expiry: string | null
  strike: number | null
  right: string | null
  action: string
  order_type: string
  quantity: number
  filled: number
  remaining: number
  limit_price: number | null
  stop_price: number | null
  time_in_force: string
  status: string
}

export interface OpenOrdersState {
  available: boolean
  orders: OpenOrder[]
}

export type AppTab = 'dashboard' | 'orders' | 'chat' | 'signals' | 'signal-history' | 'gamma' | 'macro' | 'settings'

export type RiskProfile = 'conservative' | 'moderate' | 'aggressive'

export interface SignalStatus {
  ib: 'connected' | 'reconnecting' | 'down'
  stream: 'idle' | 'warming_up' | 'streaming' | 'error'
  error: string | null
  symbol: string
  timeframe_minutes: number
  llm: {
    enabled: boolean
    configured: boolean
    provider: string | null
    model: string | null
  }
}

export interface SignalIndicators {
  vwap: number | null
  vwap_std?: number | null // missing on signals recorded before the VWAP band trigger
  ema_fast: number | null
  ema_slow: number | null
  bb_mid: number | null
  bb_upper: number | null
  bb_lower: number | null
  rvol: number | null
}

export interface SignalBar {
  time: string // bar start
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface SignalChartPoint extends SignalBar, SignalIndicators {}

export interface SignalChart {
  timeframe_minutes: number
  bars: SignalChartPoint[]
}

export interface SignalLive {
  last_price: number | null
  last_price_time: string | null
  bar_time: string | null
  bar_close: number | null
  indicators: SignalIndicators | null
  forming: SignalBar | null
}

export interface LLMDecision {
  action: 'take' | 'skip' | 'unfiltered'
  confidence: number | null
  reason: string
  provider: string | null
  model: string | null
}

export type SignalCategory = 'volume' | 'technical'

export interface SignalRecord {
  id: string
  time: string
  symbol: string
  signal_type: string
  category?: SignalCategory // missing on signals recorded before triggers had categories
  ema_periods?: [number, number] // fast, slow; missing on older signals
  price: number
  indicators: SignalIndicators
  bars: { time: string; open: number; high: number; low: number; close: number; volume: number }[]
  llm: LLMDecision
  notified: boolean
}

export type SignalAnalysisKind = 'pre' | 'post'

export interface AnalysisMeta {
  kind: SignalAnalysisKind
  created_at: string
  provider: string
  model: string
}

export interface PreMortem extends AnalysisMeta {
  kind: 'pre'
  action: 'take' | 'skip'
  confidence: number
  case_for: string
  risks: string
  invalidation: string
}

export interface SignalOutcomes {
  return_pct: { '15m': number | null; '30m': number | null; '60m': number | null; close: number | null }
  largest_gain_pct: number | null
  largest_loss_pct: number | null
  returned_to_start: boolean
}

export interface PostMortem extends AnalysisMeta {
  kind: 'post'
  verdict: 'good' | 'bad' | 'mixed'
  explanation: string
  directions: string[]
  outcomes: SignalOutcomes
  hindsight: boolean
}

export type SignalAnalysis = PreMortem | PostMortem

export type SignalHistoryRecord = Omit<SignalRecord, 'bars'> & {
  analyses?: { pre?: PreMortem; post?: PostMortem }
}

export interface SignalHistoryPage {
  signals: SignalHistoryRecord[]
  next_cursor: string | null
}

export interface SignalSettings {
  symbol: string
  timeframe_minutes: number
  ema_fast: number
  ema_slow: number
  bb_period: number
  bb_std: number
  rvol_period: number
  rvol_threshold: number
  trigger_volume_enabled: boolean
  trigger_ema_enabled: boolean
  trigger_vwap_enabled: boolean
  trigger_vwap_band_enabled: boolean
  vwap_band_std: number
  include_premarket: boolean
  open_blackout_minutes: number
  close_blackout_minutes: number
  cooldown_minutes: number
  llm_enabled: boolean
  llm_confidence_threshold: number
  llm_model_anthropic: string
  llm_model_openai: string
  llm_model_openrouter: string
}

export interface SignalState {
  status: SignalStatus
  live: SignalLive
  chart: SignalChart
  history: SignalRecord[]
  settings: SignalSettings
}

export interface GammaStrike {
  strike: number
  call: number
  put: number
  net: number
  call_oi: number
  put_oi: number
}

export interface GammaExpiry {
  expiry: string
  call: number
  put: number
  net: number
  call_oi: number
  put_oi: number
}

export interface GammaResult {
  symbol: string
  updated_at: string
  market_open: boolean
  spot: number
  net_gex: number
  call_gex: number
  put_gex: number
  call_wall: number | null
  put_wall: number | null
  zero_gamma: number | null
  strikes: GammaStrike[]
  expiries: GammaExpiry[]
  contracts: number
  expirations: string[]
  strike_range: [number, number]
  open_interest: { live: number; cached: number; missing: number; cached_as_of: string | null }
}

export interface GammaSettings {
  symbol: string
  max_days: number
  strike_range_pct: number
  refresh_minutes: number
  risk_free_rate: number
}

export interface GammaState {
  refreshing: boolean
  progress: { done: number; total: number }
  error: string | null
  result: GammaResult | null
  settings: GammaSettings
  connected: boolean
}

// ── Macro ────────────────────────────────────────────────────────────────────

export type MacroFreshness = 'live' | 'delayed' | 'closed' | 'daily'

export interface MacroIndicator {
  key: string
  label: string
  unit: string
  change_mode: 'pct' | 'bp'
  decimals: number
  contract: string | null
  contract_month: string | null // YYYYMM, futures only
  value: number | null
  previous_close: number | null
  change: number | null
  change_pct: number | null
  change_bp: number | null
  market_open: boolean
  freshness: MacroFreshness
  valid_from: string | null // YYYY-MM-DD, daily rates only
  valid_to: string | null
  updated_at: string | null
  stale: boolean
  error: string | null
  sparkline: { time: number; value: number }[]
}

export interface SentimentComponent {
  key: string
  label: string
  detail: string
  meaning: string
  score: number | null
  in_score: boolean
  error: string | null
}

export interface MarketSentiment {
  score: number | null
  band: string | null
  as_of: string | null // YYYY-MM-DD of the latest daily close used
  components: SentimentComponent[]
  history: { time: number; value: number }[]
  stale: boolean
}

export interface MacroState {
  connected: boolean
  indicators: MacroIndicator[]
  sentiment: MarketSentiment | null
}
