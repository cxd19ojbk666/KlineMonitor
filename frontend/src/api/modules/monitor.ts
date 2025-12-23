import request from '../request'
import type { SymbolMonitorListResponse, SymbolMonitorData } from '@/types'

export const getMonitorData = (params: {
  skip?: number
  limit?: number
  symbol?: string
  interval?: string
  kline_limit?: number
}): Promise<SymbolMonitorListResponse> => {
  return request.get('/monitor/data', { params })
}

export const getSymbolMonitorData = (
  symbol: string,
  interval: string = '15m',
  kline_limit: number = 50
): Promise<SymbolMonitorData> => {
  return request.get(`/monitor/data/${symbol}`, { params: { interval, kline_limit } })
}

export const getKlines = (
  symbol: string,
  interval: string = '15m',
  limit: number = 100
) => {
  return request.get(`/monitor/klines/${symbol}`, { params: { interval, limit } })
}
