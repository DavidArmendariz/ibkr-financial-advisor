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
  AvailableFunds?: number
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

export interface FilledOrder {
  perm_id: number
  symbol: string
  asset_class: string
  currency: string
  expiry: string | null
  strike: number | null
  right: string | null
  action: string
  quantity: number
  average_price: number
  venue: string
  commission: number | null
  realized_pnl: number | null
  time: string
}

export interface FilledOrdersState {
  available: boolean
  orders: FilledOrder[]
}

export interface OpenOrdersState {
  available: boolean
  orders: OpenOrder[]
}

export type AppTab = 'dashboard' | 'orders' | 'chat' | 'signals' | 'signal-history' | 'trade-planner' | 'gamma' | 'macro' | 'global-markets' | 'sector-rotation' | 'fundamentals' | 'calendar' | 'settings'

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
  rsi?: number | null // missing on signals recorded before the RSI trigger
  ema_fast: number | null
  ema_slow: number | null
  bb_mid: number | null
  bb_upper: number | null
  bb_lower: number | null
  rvol: number | null
  atr?: number | null // missing on signals recorded before ATR
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

export interface VolumeProfileLevels {
  session: string
  poc: number
  value_area_high: number
  value_area_low: number
}

export interface VolumeProfileBars extends VolumeProfileLevels {
  bucket: number
  buckets: { price: number; volume: number }[]
}

export interface VolumeProfile {
  bars: VolumeProfileBars | null
  today: VolumeProfileLevels | null
  yesterday: VolumeProfileLevels | null
}

export interface SignalLive {
  last_price: number | null
  last_price_time: string | null
  bar_time: string | null
  bar_close: number | null
  indicators: SignalIndicators | null
  forming: SignalBar | null
  volume_profile?: VolumeProfile | null
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

export interface SignalOutcome {
  status: 'measured' | 'not_available'
  move_5m: number | null
  move_15m: number | null
  move_30m: number | null
  max_up: number | null
  max_down: number | null
}

export type SignalHistoryRecord = Omit<SignalRecord, 'bars'> & {
  analyses?: { pre?: PreMortem; post?: PostMortem }
  outcome?: SignalOutcome | null
}

export type OutcomeHorizon = '5m' | '15m' | '30m'

export interface OutcomeHorizonStats {
  count: number
  average: number | null
  median: number | null
  up_share: number | null
  small_sample: boolean
}

export interface OutcomeStats {
  horizons: Record<OutcomeHorizon, OutcomeHorizonStats>
  average_max_up: number | null
  average_max_down: number | null
}

export interface SignalOutcomeResults {
  triggers: (OutcomeStats & { signal_type: string })[]
  baseline: OutcomeStats | null
  baseline_days: number
  pending: number
  min_sample: number
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
  trigger_ema_down_enabled: boolean
  trigger_vwap_enabled: boolean
  trigger_vwap_band_enabled: boolean
  vwap_band_std: number
  trigger_rsi_enabled: boolean
  rsi_period: number
  atr_period: number
  rsi_upper: number
  rsi_lower: number
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

// ── Calendar ─────────────────────────────────────────────────────────────────

export interface CalendarEventRecord {
  id: string
  name: string
  category: 'economic' | 'earnings'
  importance: 'high' | 'medium'
  day: string // YYYY-MM-DD in ET
  at: string | null
  timing: 'before_open' | 'after_close' | null
  source: string
}

export interface CalendarSource {
  key: string
  label: string
  configured: boolean
  updated_at: string | null
  error: string | null
}

export interface CalendarSettings {
  fred_key_set: boolean
  fred_key_hint: string | null
  finnhub_key_set: boolean
  finnhub_key_hint: string | null
  earnings_symbols: string[]
  alert_evening_enabled: boolean
  alert_soon_enabled: boolean
}

export interface CalendarState {
  events: CalendarEventRecord[]
  sources: CalendarSource[]
  settings: CalendarSettings
}

// ── Asia & Europe ────────────────────────────────────────────────────────────

export interface GlobalInstrument {
  key: string
  label: string
  section: string
  group: string
  currency: string
  unit: string
  decimals: number
  tz: string
  place: string
  value: number | null
  previous_close: number | null
  change: number | null
  change_pct: number | null
  market_open: boolean
  data_time: number | null
  delay_minutes: number | null
  stale: boolean
  error: string | null
  sparkline: { time: number; value: number }[]
}

export interface GlobalMarketsState {
  connected: boolean
  instruments: GlobalInstrument[]
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
  delay_minutes?: number | null
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

// ── Trade Planner ────────────────────────────────────────────────────────────

export type PlannerSymbol = 'SOXL' | 'SOXS'
export type AtrBasis = 'intraday' | 'daily'

export interface PlannerSettings {
  symbol: PlannerSymbol
  atr_basis: AtrBasis
  stop_multiple: number
  target_multiple: number
  risk_mode: 'percent' | 'dollars'
  risk_percent: number
  risk_dollars: number
}

export interface PlannerQuote {
  symbol: PlannerSymbol
  price: number | null
  price_time: string | null
  intraday_atr: number | null
  intraday_pct: number | null
  intraday_time: string | null
  daily_atr: number | null
  daily_pct: number | null
  daily_time: string | null
  bid: number | null
  ask: number | null
  quote_time: string | null
  quote_delayed: boolean
  error: string | null
}

export interface PlannerState {
  connected: boolean
  mode: 'live' | 'paper' | null
  account: { net_liquidation: number | null; available_funds: number | null } | null
  settings: PlannerSettings
  intraday_minutes: number
  intraday_period: number
  daily_period: number
  quotes: PlannerQuote[]
}

export type TradePlan =
  | {
      ok: true
      entry: number
      stop: number
      target: number
      stop_pct: number
      target_pct: number
      shares: number
      position_value: number
      risk_dollars: number
      reward_dollars: number
      reward_risk: number
      exceeds_funds: boolean
    }
  | { ok: false; reason: string }

// ── Sector rotation ──────────────────────────────────────────────────────────

export type RotationQuadrant = 'Leading' | 'Weakening' | 'Lagging' | 'Improving'
export type RotationTimeframe = 'weekly' | 'daily'

export interface RotationPoint {
  time: number // unix seconds, midnight UTC of the session
  ratio: number
  momentum: number
  quadrant: RotationQuadrant
}

export interface RotationSeries {
  points: RotationPoint[]
  periods: number
}

export interface RotationEtf {
  symbol: string
  name: string
  error: string | null
  weekly: RotationSeries
  daily: RotationSeries
}

export interface RotationSettings {
  timeframe: RotationTimeframe
  tail: number
}

export interface RotationState {
  connected: boolean
  stale: boolean
  fetched_at: string | null
  last_session: number | null
  benchmark: { symbol: string; error: string | null }
  lookback: number
  settings: RotationSettings
  etfs: RotationEtf[]
}

// ── Fundamentals ─────────────────────────────────────────────────────────────

export interface FundamentalsMultiple {
  key: string
  label: string
  value: number | null
  status: 'ok' | 'missing' | 'not_meaningful'
  peer_median: number | null
  peer_count: number
  cheaper_than_peers: boolean | null
  has_history: boolean
  history_median: number | null
  history_years: number
  cheaper_than_history: boolean | null
}

export interface FundamentalsQuality {
  key: string
  label: string
  value: number | null
  unit: '%' | 'x'
}

export interface AnalystRatingMonth {
  period: string
  strong_buy: number
  buy: number
  hold: number
  sell: number
  strong_sell: number
  total: number
  buy_share: number | null
}

export interface FundamentalsNews {
  time: number // unix seconds
  source: string
  headline: string
  url: string | null
  provider: string // 'finnhub' or an IBKR provider code
  article_id: string | null
}

export interface FundamentalsWriteUp {
  created_at: string
  data_time: string
  provider: string
  model: string
  bull_case: string
  bear_case: string
  valuation_view: string
  watch: string
}

export interface FundamentalsLookup {
  ticker: string
  name: string | null
  industry: string | null
  exchange: string | null
  currency: string | null
  price: number | null
  change_pct: number | null
  market_cap_millions: number | null
  multiples: FundamentalsMultiple[]
  quality: FundamentalsQuality[]
  peers: string[]
  ratings: { latest: AnalystRatingMonth; previous: AnalystRatingMonth | null } | null
  news: FundamentalsNews[]
  news_notes: string[]
  fetched_at: string
  analysis: FundamentalsWriteUp | null
}

export type FundamentalsErrorCode = 'no_key' | 'not_found' | 'bad_ticker' | 'rate_limited' | 'finnhub' | 'no_provider' | 'error'
