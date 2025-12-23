import request from '../request'
import type { Config } from '@/types'

export const getConfigs = (): Promise<Config[]> => {
  return request.get('/config')
}

export const updateConfig = (key: string, value: string): Promise<Config> => {
  return request.put(`/config/${key}`, { value })
}

export const batchUpdateConfigs = (configs: { key: string; value: string }[]) => {
  return request.post('/config/batch', { configs })
}
