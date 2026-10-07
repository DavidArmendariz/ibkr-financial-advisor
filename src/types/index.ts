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

export type AppTab = 'dashboard' | 'chat' | 'signals' | 'settings'

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
  ema_fast: number | null
  ema_slow: number | null
  bb_mid: number | null
  bb_upper: number | null
  bb_lower: number | null
  rvol: number | null
}

export interface SignalLive {
  last_price: number | null
  last_price_time: string | null
  bar_time: string | null
  bar_close: number | null
  indicators: SignalIndicators | null
}

export interface LLMDecision {
  action: 'take' | 'skip' | 'unfiltered'
  confidence: number | null
  reason: string
  provider: string | null
  model: string | null
}

export interface SignalRecord {
  id: string
  time: string
  symbol: string
  signal_type: string
  price: number
  indicators: SignalIndicators
  bars: { time: string; open: number; high: number; low: number; close: number; volume: number }[]
  llm: LLMDecision
  notified: boolean
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
  history: SignalRecord[]
  settings: SignalSettings
}
