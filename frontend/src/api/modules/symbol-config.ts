import request from '../request'
import type { SymbolConfig, SymbolConfigListResponse } from '@/types'

export interface SymbolConfigParams {
  skip?: number
  limit?: number
  symbol?: string
  interval?: string
}

export interface SymbolConfigCreateData {
  symbol: string
  interval: string
  price_error?: number | null
  middle_kline_cnt?: number | null
  fake_kline_cnt?: number | null
}

export interface SymbolConfigUpdateData {
  price_error?: number | null
  middle_kline_cnt?: number | null
  fake_kline_cnt?: number | null
}

export const getSymbolConfigs = (params?: SymbolConfigParams): Promise<SymbolConfigListResponse> => {
  return request.get('/config/symbol-configs', { params })
}

export const getSymbolConfig = (symbol: string, interval: string): Promise<SymbolConfig> => {
  return request.get(`/config/symbol-configs/${symbol}/${interval}`)
}

export const createSymbolConfig = (data: SymbolConfigCreateData): Promise<SymbolConfig> => {
  return request.post('/config/symbol-configs', data)
}

export const updateSymbolConfig = (
  symbol: string,
  interval: string,
  data: SymbolConfigUpdateData
): Promise<SymbolConfig> => {
  return request.put(`/config/symbol-configs/${symbol}/${interval}`, data)
}

export const deleteSymbolConfig = (symbol: string, interval: string) => {
  return request.delete(`/config/symbol-configs/${symbol}/${interval}`)
}
