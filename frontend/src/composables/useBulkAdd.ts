import { ref, reactive } from 'vue'
import { getAvailableSymbols, bulkAddAllSymbols } from '@/api'
import type { BulkAddProgress, AvailableSymbolsResponse } from '@/types'

export interface BulkAddLog {
  symbol: string
  status: string
}

export function useBulkAdd() {
  const showConfirmDialog = ref(false)
  const showProgressDialog = ref(false)
  const loading = ref(false)
  const complete = ref(false)
  const progress = ref(0)
  const message = ref('')
  const phase = ref('')
  const total = ref(0)
  const current = ref(0)
  const currentSymbol = ref('')
  const result = reactive({ added: 0, synced: 0, failed: 0, stats: [] as string[] })
  const logs = ref<BulkAddLog[]>([])
  const availableInfo = ref<AvailableSymbolsResponse | null>(null)

  const fetchAvailableSymbols = async () => {
    availableInfo.value = null
    showConfirmDialog.value = true
    try {
      availableInfo.value = await getAvailableSymbols()
    } catch {
      // error handled by caller
    }
  }

  const startBulkAdd = (onComplete?: () => void) => {
    showConfirmDialog.value = false
    
    // 重置状态
    complete.value = false
    progress.value = 0
    message.value = '准备中...'
    phase.value = ''
    total.value = 0
    current.value = 0
    currentSymbol.value = ''
    result.added = 0
    result.synced = 0
    result.failed = 0
    result.stats = []
    logs.value = []
    
    showProgressDialog.value = true
    
    bulkAddAllSymbols(
      (data: BulkAddProgress) => {
        phase.value = data.phase
        if (data.message) message.value = data.message
        if (data.progress !== undefined) progress.value = data.progress
        if (data.phase === 'info' && data.total !== undefined) total.value = data.total
        
        // 处理并发同步进度（新格式）
        if (data.phase === 'syncing') {
          if (data.completed !== undefined) current.value = data.completed
          if (data.total !== undefined) total.value = data.total
          if (data.synced_klines !== undefined) result.synced = data.synced_klines
        }
        
        // 兼容旧的串行格式
        if (data.phase === 'adding') {
          if (data.current !== undefined) current.value = data.current
          if (data.total !== undefined) total.value = data.total
          if (data.symbol) {
            currentSymbol.value = data.symbol
            const existingLog = logs.value.find(l => l.symbol === data.symbol)
            if (existingLog) {
              existingLog.status = data.status || 'syncing'
            } else {
              logs.value.push({ symbol: data.symbol, status: data.status || 'syncing' })
            }
          }
        }
        
        if (data.phase === 'complete') {
          complete.value = true
          progress.value = 100
          if (data.added !== undefined) result.added = data.added
          if (data.synced !== undefined) result.synced = data.synced
          if (data.failed !== undefined) result.failed = data.failed
          if (data.failed_tasks !== undefined) result.failed = data.failed_tasks
          if (data.stats) result.stats = data.stats
        }
      },
      () => {
        onComplete?.()
      },
      () => {
        complete.value = true
      }
    )
  }

  const closeProgressDialog = () => {
    showProgressDialog.value = false
  }

  return {
    showConfirmDialog,
    showProgressDialog,
    loading,
    complete,
    progress,
    message,
    phase,
    total,
    current,
    currentSymbol,
    result,
    logs,
    availableInfo,
    fetchAvailableSymbols,
    startBulkAdd,
    closeProgressDialog
  }
}
