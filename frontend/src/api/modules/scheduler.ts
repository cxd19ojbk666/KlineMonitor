import request from '../request'
import type { SchedulerStatus } from '@/types'

export const getSchedulerStatus = (): Promise<SchedulerStatus> => {
  return request.get('/scheduler/status')
}

export const pauseScheduler = () => {
  return request.post('/scheduler/pause')
}

export const resumeScheduler = () => {
  return request.post('/scheduler/resume')
}
