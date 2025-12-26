import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getConfigs, updateConfig, batchUpdateConfigs } from '@/api/modules/config'
import type { Config, ConfigBatchUpdate } from '@/types/config'

export const useConfigStore = defineStore('config', () => {
  // 状态
  const configs = ref<Record<string, string>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // 配置变更版本号，用于触发依赖组件刷新
  const configVersion = ref(0)

  // 计算属性 - 获取各项配置值
  const volumePercent = computed(() => parseFloat(configs.value['1_volume_percent'] || '12.5'))
  const risePercent = computed(() => parseFloat(configs.value['2_rise_percent'] || '3.0'))
  const priceError = computed(() => parseFloat(configs.value['3_price_error'] || '0.5'))
  const middleKlineCnt = computed(() => parseInt(configs.value['3_middle_kline_cnt'] || '3'))
  const fakeKlineCnt = computed(() => parseInt(configs.value['3_fake_kline_cnt'] || '2'))
  const dedupSeconds = computed(() => parseInt(configs.value['dedup_seconds'] || '300'))

  // 获取所有配置
  const fetchConfigs = async () => {
    loading.value = true
    error.value = null
    try {
      const data = await getConfigs()
      configs.value = data.reduce((acc: Record<string, string>, c: Config) => {
        acc[c.key] = c.value
        return acc
      }, {})
    } catch (e: any) {
      error.value = e.message || '获取配置失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 更新单个配置
  const updateSingleConfig = async (key: string, value: string) => {
    try {
      await updateConfig(key, value)
      configs.value[key] = value
    } catch (e: any) {
      error.value = e.message || '更新配置失败'
      throw e
    }
  }

  // 批量更新配置
  const batchUpdate = async (configList: ConfigBatchUpdate) => {
    loading.value = true
    error.value = null
    try {
      await batchUpdateConfigs(configList.configs)
      configList.configs.forEach(c => {
        configs.value[c.key] = c.value
      })
      // 触发配置变更通知
      notifyConfigChange()
    } catch (e: any) {
      error.value = e.message || '批量更新配置失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 通知配置变更
  const notifyConfigChange = () => {
    configVersion.value++
  }

  // 获取配置值
  const getConfigValue = (key: string, defaultValue: string = ''): string => {
    return configs.value[key] || defaultValue
  }

  return {
    // 状态
    configs,
    loading,
    error,
    configVersion,
    // 计算属性
    volumePercent,
    risePercent,
    priceError,
    middleKlineCnt,
    fakeKlineCnt,
    dedupSeconds,
    // 方法
    fetchConfigs,
    updateSingleConfig,
    batchUpdate,
    getConfigValue,
    notifyConfigChange
  }
})
