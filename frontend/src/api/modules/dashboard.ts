import request from '../request'
import type { DashboardStats } from '@/types'

export const getDashboard = (): Promise<DashboardStats> => {
  return request.get('/alerts/dashboard')
}
