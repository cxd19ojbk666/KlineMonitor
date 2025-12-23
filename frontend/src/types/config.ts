// 全局配置
export interface Config {
  id: number
  key: string
  value: string
}

// 配置更新
export interface ConfigUpdate {
  value: string
}

// 批量配置更新
export interface ConfigBatchUpdate {
  configs: Array<{
    key: string
    value: string
  }>
}

// 币种个性化配置
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

// 币种配置创建
export interface SymbolConfigCreate {
  symbol: string
  interval: string
  price_error?: number | null
  middle_kline_cnt?: number | null
  fake_kline_cnt?: number | null
}

// 币种配置更新
export interface SymbolConfigUpdate {
  price_error?: number | null
  middle_kline_cnt?: number | null
  fake_kline_cnt?: number | null
}
