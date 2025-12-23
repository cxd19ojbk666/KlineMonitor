import request from '../request'
import type { Symbol, SymbolListResponse, AvailableSymbolsResponse, BulkAddProgress, SyncProgress } from '@/types'

export const getSymbols = (params: {
  skip?: number
  limit?: number
  is_active?: boolean
  symbol?: string
}): Promise<SymbolListResponse> => {
  return request.get('/symbols', { params })
}

export const createSymbol = (symbol: string): Promise<Symbol> => {
  return request.post('/symbols', { symbol })
}

export const toggleSymbol = (symbol: string) => {
  return request.put(`/symbols/${symbol}/toggle`)
}

export const batchActivateSymbols = (symbols: string[], is_active: boolean) => {
  return request.put('/symbols/batch/activate', symbols, { params: { is_active } })
}

export const deleteSymbol = (symbol: string) => {
  return request.delete(`/symbols/${symbol}`)
}

export const batchDeleteSymbols = (symbols: string[]) => {
  return request.delete('/symbols/batch', { data: symbols })
}

export const getAvailableSymbols = (): Promise<AvailableSymbolsResponse> => {
  return request.get('/symbols/available')
}

// SSE批量添加所有交易对
export const bulkAddAllSymbols = (
  onProgress: (data: BulkAddProgress) => void,
  onComplete: () => void,
  onError: (error: string) => void
): EventSource => {
  const eventSource = new EventSource(`/api/symbols/bulk-add`)
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data) as BulkAddProgress
    onProgress(data)
    if (data.phase === 'complete' || data.phase === 'error') {
      setTimeout(() => {
        eventSource.close()
        if (data.phase === 'complete') {
          onComplete()
        } else {
          onError(data.message || '批量添加失败')
        }
      }, 1000)
    }
  }
  
  eventSource.onerror = () => {
    eventSource.close()
    onError('连接失败')
  }
  
  return eventSource
}

// SSE同步币种数据（90天）
export const syncSymbolData = (
  symbol: string,
  onProgress: (data: SyncProgress) => void,
  onComplete: () => void,
  onError: (error: string) => void
): EventSource => {
  const eventSource = new EventSource(`/api/symbols/${symbol}/sync`)
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onProgress(data)
    if (data.status === 'complete') {
      eventSource.close()
      onComplete()
    }
  }
  
  eventSource.onerror = () => {
    eventSource.close()
    onError('同步连接失败')
  }
  
  return eventSource
}
