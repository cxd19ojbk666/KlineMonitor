import { logger } from '@/utils/logger'

export interface SSEEvent {
  type: string
  data: Record<string, unknown>
  timestamp: string
}

export type SSEEventHandler = (event: SSEEvent) => void

/**
 * 创建 SSE 事件流连接
 * 用于接收后端调度器完成数据同步后的通知
 */
export const createEventSource = (
  onEvent: SSEEventHandler,
  onError?: (error: Event) => void
): EventSource => {
  const eventSource = new EventSource('/api/events')
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as SSEEvent
      onEvent(data)
    } catch (e) {
      logger.error('SSE数据解析失败', e, { sampling: 5000 })
    }
  }
  
  eventSource.onerror = (error) => {
    logger.error('SSE连接错误', error, { sampling: 10000 })
    onError?.(error)
  }
  
  return eventSource
}
