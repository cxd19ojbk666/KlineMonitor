import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { logger } from '@/utils/logger'

// 创建axios实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 可以在这里添加token等认证信息
    // const token = localStorage.getItem('token')
    // if (token && config.headers) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error: AxiosError) => {
    logger.error('请求发送失败', error, { sampling: 3000 })
    ElMessage.error('请求发送失败')
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 直接返回响应数据
    return response.data
  },
  (error: AxiosError) => {
    // 统一错误处理
    const status = error.response?.status
    const message = (error.response?.data as any)?.detail || error.message
    
    switch (status) {
      case 400:
        ElMessage.error(`请求错误: ${message}`)
        break
      case 401:
        ElMessage.error('未授权，请重新登录')
        // 可以在这里跳转到登录页
        // router.push('/login')
        break
      case 403:
        ElMessage.error('拒绝访问')
        break
      case 404:
        ElMessage.error(`请求的资源不存在: ${message}`)
        break
      case 422:
        // Pydantic验证错误
        const validationErrors = (error.response?.data as any)?.detail
        if (Array.isArray(validationErrors)) {
          const errorMsg = validationErrors.map((err: any) => 
            `${err.loc?.join('.')}: ${err.msg}`
          ).join('; ')
          ElMessage.error(`数据验证失败: ${errorMsg}`)
        } else {
          ElMessage.error(`数据验证失败: ${message}`)
        }
        break
      case 500:
        ElMessage.error('服务器错误，请稍后重试')
        break
      case 502:
        ElMessage.error('网关错误')
        break
      case 503:
        ElMessage.error('服务不可用')
        break
      case 504:
        ElMessage.error('网关超时')
        break
      default:
        if (error.code === 'ECONNABORTED') {
          ElMessage.error('请求超时，请检查网络连接')
        } else if (error.message.includes('Network Error')) {
          ElMessage.error('网络错误，请检查网络连接')
        } else {
          ElMessage.error(`请求失败: ${message}`)
        }
    }
    
    logger.error('API请求失败', { status, message, url: error.config?.url }, { sampling: 5000 })
    
    return Promise.reject(error)
  }
)

export default request
