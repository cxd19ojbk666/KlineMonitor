/**
 * 时间工具函数
 * 统一处理北京时间（UTC+8）
 */
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

// 扩展 dayjs 支持时区
dayjs.extend(utc)
dayjs.extend(timezone)

// 设置默认时区为北京时间
dayjs.tz.setDefault('Asia/Shanghai')

/**
 * 格式化时间为北京时间
 * @param time 时间字符串或 Date 对象
 * @param format 格式化模板，默认 'YYYY-MM-DD HH:mm'
 */
export const formatBeijingTime = (time: string | Date, format = 'YYYY-MM-DD HH:mm'): string => {
  if (!time) return '-'
  return dayjs(time).format(format)
}

/**
 * 格式化时间为短格式（月-日 时:分）
 */
export const formatShortTime = (time: string | Date): string => {
  if (!time) return '-'
  return dayjs(time).format('MM-DD HH:mm')
}

/**
 * 格式化时间为完整格式
 */
export const formatFullTime = (time: string | Date): string => {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 获取当前北京时间
 */
export const nowBeijing = (): dayjs.Dayjs => {
  return dayjs().tz('Asia/Shanghai')
}

export default dayjs
