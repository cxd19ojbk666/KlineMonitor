import request from '../request'
import type { AlertListResponse } from '@/types'

export const getAlerts = (params: {
  skip?: number
  limit?: number
  alert_type?: number
  symbol?: string
  start_time?: string
  end_time?: string
}): Promise<AlertListResponse> => {
  return request.get('/alerts', { params })
}

export const deleteAlert = (id: number) => {
  return request.delete(`/alerts/${id}`)
}

export const deleteAllAlerts = (alert_type?: number) => {
  return request.delete('/alerts', { params: { alert_type } })
}
