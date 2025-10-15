export interface User {
  id: string
  email: string
  username: string
  status: string
  created_at: string
}

export interface TradingAccount {
  id: string
  mt5_login: string
  broker: string
  account_type: string
  balance: number
  connection_status: string
  websocket_connection_id?: string
  pytrader_ea_version?: string
  last_ping?: string
  created_at: string
}

export interface AIStrategy {
  id: string
  name: string
  llm_model: string
  strategy_config: Record<string, any>
  performance_metrics: Record<string, any>
  status: string
  created_at: string
  updated_at?: string
}

export interface Trade {
  id: string
  symbol: string
  type: 'BUY' | 'SELL'
  volume: number
  open_price: number
  close_price?: number
  stop_loss?: number
  take_profit?: number
  profit_loss: number
  commission: number
  status: string
  mt5_order_id?: string
  mt5_position_id?: string
  opened_at: string
  closed_at?: string
  strategy_name?: string
}

export interface DashboardStats {
  total_accounts: number
  online_accounts: number
  active_strategies: number
  open_trades: number
  total_profit_loss: number
  todays_trades: number
  commission_earned: number
}

export interface PerformanceMetrics {
  total_trades: number
  win_rate: number
  average_profit: number
  sharpe_ratio: number
  max_drawdown: number
  profit_factor: number
}

export interface ApiResponse<T = any> {
  data: T
  message?: string
  error?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

export interface MarketData {
  symbol: string
  price: number
  timestamp: string
  volume?: number
  ohlc?: {
    open: number
    high: number
    low: number
    close: number
  }
}

export interface TradingSignal {
  id: string
  symbol: string
  type: 'BUY' | 'SELL'
  volume: number
  price: number
  stop_loss?: number
  take_profit?: number
  confidence: number
  reason: string
  timestamp: string
  strategy_id: string
  strategy_name: string
}

export interface Commission {
  id: string
  trade_id: string
  user_id: string
  amount: number
  volume_commission: number
  profit_commission: number
  status: string
  created_at: string
  processed_at?: string
}
