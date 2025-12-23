import type { PaginatedResponse } from './common'

// 类型1：成交量提醒数据
export interface VolumeAlertData {
  volume_15m: number
  volume_8h: number
  volume_ratio: number
  volume_threshold: number
}

// 类型2：涨幅提醒数据
export interface RiseAlertData {
  rise_percent: number
  rise_threshold: number
  rise_start_price: number
  rise_end_price: number
}

// 类型3：开盘价匹配数据
export interface OpenPriceAlertData {
  timeframe: string
  price_d: number
  price_e: number
  time_d: string
  time_e: string
  price_error: number
  price_error_threshold: number
  middle_count: number
  middle_count_threshold: number
}

export type AlertData = VolumeAlertData | RiseAlertData | OpenPriceAlertData

export interface Alert {
  id: number
  symbol: string
  alert_type: number
  data: AlertData
  created_at: string
}

export type AlertListResponse = PaginatedResponse<Alert>
