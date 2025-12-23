import { ref } from 'vue'
import { syncSymbolData } from '@/api'
import type { SyncProgress } from '@/types'

export interface SyncDetail {
  interval: string
  status: string
  count?: number
}

export function useSymbolSync() {
  const showSyncDialog = ref(false)
  const syncingSymbol = ref('')
  const syncProgress = ref(0)
  const syncComplete = ref(false)
  const currentInterval = ref('')
  const syncDetails = ref<SyncDetail[]>([])

  const startSync = (symbol: string) => {
    syncingSymbol.value = symbol
    syncProgress.value = 0
    syncComplete.value = false
    currentInterval.value = ''
    syncDetails.value = []
    showSyncDialog.value = true

    return syncSymbolData(
      symbol,
      (data: SyncProgress) => {
        syncProgress.value = data.progress
        if (data.interval) {
          currentInterval.value = data.interval
          const existingIdx = syncDetails.value.findIndex(d => d.interval === data.interval)
          if (existingIdx >= 0) {
            syncDetails.value[existingIdx] = {
              interval: data.interval,
              status: data.status,
              count: data.count
            }
          } else {
            syncDetails.value.push({
              interval: data.interval,
              status: data.status,
              count: data.count
            })
          }
        }
        if (data.status === 'complete') {
          syncComplete.value = true
          syncProgress.value = 100
        }
      },
      () => { /* onComplete */ },
      () => {
        syncComplete.value = true
      }
    )
  }

  const closeSyncDialog = () => {
    showSyncDialog.value = false
  }

  return {
    showSyncDialog,
    syncingSymbol,
    syncProgress,
    syncComplete,
    currentInterval,
    syncDetails,
    startSync,
    closeSyncDialog
  }
}
