import type { PaginatedResponse } from './common'

export interface Symbol {
  id: number
  symbol: string
  is_active: boolean
  created_at: string
}

export type SymbolListResponse = PaginatedResponse<Symbol>

export interface SymbolConfig {
  id: number
  symbol: string
  interval: string
  price_error: number | null
  middle_kline_cnt: number | null
  fake_kline_cnt: number | null
  created_at: string
  updated_at: string
}

export type SymbolConfigListResponse = PaginatedResponse<SymbolConfig>

export interface AvailableSymbolsResponse {
  total_binance: number
  existing: number
  available: number
  symbols: string[]
}

export interface BulkAddProgress {
  phase: 'init' | 'fetch' | 'info' | 'adding' | 'syncing' | 'db_done' | 'sync_start' | 'complete' | 'error' | 'cleanup'
  message?: string
  progress?: number
  total?: number
  existing?: number
  current?: number
  symbol?: string
  status?: 'syncing' | 'done' | 'error' | 'partial'
  error?: string
  added?: number
  synced?: number
  failed?: number
  // 新增：并发同步相关字段
  completed?: number
  synced_klines?: number
  success_tasks?: number
  failed_tasks?: number
  stats?: string[]
}

export interface SyncProgress {
  progress: number
  interval?: string
  status: string
  count?: number
  error?: string
}
