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

export type AppTab = 'dashboard' | 'chat' | 'settings'
