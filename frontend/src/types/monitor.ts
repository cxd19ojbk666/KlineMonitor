import type { PaginatedResponse } from './common'

export interface KlineData {
  open_time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  quote_volume: number
  close_time: string
}

export interface MonitorMetrics {
  volume_15m: number
  volume_8h: number
  volume_percent: number
  volume_threshold: number
  volume_triggered: boolean
  rise_percent: number
  rise_threshold: number
  rise_triggered: boolean
  rise_start_time?: string
  rise_start_price?: number
  rise_end_time?: string
  rise_end_price?: number
  price_error_config: number
  fake_count_n_config: number
  open_price_triggered: boolean
  open_price_match_info: string | null
  open_price_d: number | null
  open_price_d_time: string | null
  open_price_e: number | null
  open_price_e_time: string | null
  open_price_error: number | null
  open_price_middle_count: number | null
}

export interface SymbolMonitorData {
  symbol: string
  timestamp: string
  current_price: number
  metrics: MonitorMetrics
  klines: KlineData[]
}

export type SymbolMonitorListResponse = PaginatedResponse<SymbolMonitorData>

export interface DashboardStats {
  total_alerts_today: number
  alert_type_1_count: number
  alert_type_2_count: number
  alert_type_3_count: number
  is_running: boolean
  recent_alerts: import('./alert').Alert[]
}

export interface SchedulerStatus {
  is_running: boolean
  is_paused: boolean
}

// Re-export SSEEvent from api for convenience
export type { SSEEvent } from '@/api/sse'
