import request from '../request'

export interface LogFile {
  name: string
  type: 'app' | 'error'
  date: string
  size: number
  modified: string
}

export interface LogContent {
  file_name: string
  total_lines: number
  lines: string[]
  has_more: boolean
}

export const getLogFiles = (): Promise<LogFile[]> => {
  return request.get('/logs/files')
}

export const getLogContent = (fileName: string, params?: {
  tail?: number
  search?: string
}): Promise<LogContent> => {
  return request.get(`/logs/content/${fileName}`, { params })
}

export const getTodayLogs = (params?: {
  log_type?: 'app' | 'error'
  tail?: number
  search?: string
}): Promise<LogContent> => {
  return request.get('/logs/today', { params })
}
