/**
 * 前端日志管理器
 * 支持日志级别控制、采样、聚合等功能
 * 针对大规模交易对场景优化
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogOptions {
  sampling?: number
  context?: Record<string, any>
}

interface ErrorCache {
  count: number
  lastTime: number
  firstTime: number
}

class Logger {
  private isDev: boolean
  private level: LogLevel
  private errorCache: Map<string, ErrorCache>
  private readonly MAX_CACHE_SIZE = 100

  constructor() {
    this.isDev = import.meta.env.DEV
    this.level = this.isDev ? 'debug' : 'error'
    this.errorCache = new Map()
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error']
    return levels.indexOf(level) >= levels.indexOf(this.level)
  }

  private getCacheKey(message: string, context?: Record<string, any>): string {
    return context ? `${message}:${JSON.stringify(context)}` : message
  }

  private checkSampling(key: string, sampling: number): boolean {
    const now = Date.now()
    const cached = this.errorCache.get(key)

    if (cached && now - cached.lastTime < sampling) {
      cached.count++
      return false
    }

    if (this.errorCache.size >= this.MAX_CACHE_SIZE) {
      const oldestKey = Array.from(this.errorCache.entries())
        .sort((a, b) => a[1].lastTime - b[1].lastTime)[0][0]
      this.errorCache.delete(oldestKey)
    }

    this.errorCache.set(key, {
      count: cached ? cached.count + 1 : 1,
      lastTime: now,
      firstTime: cached?.firstTime || now
    })

    return true
  }

  private formatMessage(level: LogLevel, message: string, context?: Record<string, any>): string {
    const timestamp = new Date().toISOString()
    const contextStr = context ? ` ${JSON.stringify(context)}` : ''
    return `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`
  }

  debug(message: string, data?: any, options?: LogOptions): void {
    if (!this.shouldLog('debug')) return

    const key = this.getCacheKey(message, options?.context)
    if (options?.sampling && !this.checkSampling(key, options.sampling)) return

    if (this.isDev) {
      console.log(this.formatMessage('debug', message, options?.context), data || '')
    }
  }

  info(message: string, data?: any, options?: LogOptions): void {
    if (!this.shouldLog('info')) return

    const key = this.getCacheKey(message, options?.context)
    if (options?.sampling && !this.checkSampling(key, options.sampling)) return

    if (this.isDev) {
      console.log(this.formatMessage('info', message, options?.context), data || '')
    }
  }

  warn(message: string, data?: any, options?: LogOptions): void {
    if (!this.shouldLog('warn')) return

    const key = this.getCacheKey(message, options?.context)
    if (options?.sampling && !this.checkSampling(key, options.sampling)) return

    console.warn(this.formatMessage('warn', message, options?.context), data || '')
  }

  error(message: string, error?: any, options?: LogOptions): void {
    if (!this.shouldLog('error')) return

    const key = this.getCacheKey(message, options?.context)
    if (options?.sampling && !this.checkSampling(key, options.sampling)) return

    if (this.isDev) {
      console.error(this.formatMessage('error', message, options?.context), error || '')
    }
  }

  getErrorStats(key?: string): ErrorCache | Map<string, ErrorCache> {
    if (key) {
      return this.errorCache.get(key) || { count: 0, lastTime: 0, firstTime: 0 }
    }
    return new Map(this.errorCache)
  }

  clearCache(): void {
    this.errorCache.clear()
  }
}

export const logger = new Logger()
export default logger
