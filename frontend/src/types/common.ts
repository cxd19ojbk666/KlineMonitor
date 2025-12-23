// API响应基础类型
export interface ApiResponse<T = any> {
  code?: number
  message?: string
  data: T
}

// 分页响应基础类型
export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

// 分页请求参数
export interface PaginationParams {
  skip?: number
  limit?: number
}

// 通用操作响应
export interface OperationResponse {
  message: string
  success?: boolean
}

// 错误响应类型
export interface ErrorResponse {
  detail: string | ValidationError[]
}

// 验证错误详情
export interface ValidationError {
  loc: (string | number)[]
  msg: string
  type: string
}
