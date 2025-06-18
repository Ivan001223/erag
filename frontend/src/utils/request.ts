import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse, type AxiosError } from 'axios'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import router from '@/router'
import { getToken, removeToken } from './auth'
import type { ApiResponse } from '@/types'

// 请求配置接口
interface RequestConfig extends AxiosRequestConfig {
  showLoading?: boolean
  showError?: boolean
  showSuccess?: boolean
  loadingText?: string
  errorMessage?: string
  successMessage?: string
  timeout?: number
  retries?: number
  retryDelay?: number
}

// 响应拦截器配置
interface ResponseConfig {
  showMessage: boolean
  showError: boolean
  redirectOnUnauthorized: boolean
}

// 创建axios实例
const service: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_APP_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json;charset=UTF-8'
  }
})

// 加载实例
let loadingInstance: any = null
let loadingCount = 0

// 显示加载
const showLoading = (text = '加载中...') => {
  if (loadingCount === 0) {
    loadingInstance = ElLoading.service({
      text,
      background: 'rgba(0, 0, 0, 0.7)',
      spinner: 'el-icon-loading'
    })
  }
  loadingCount++
}

// 隐藏加载
const hideLoading = () => {
  loadingCount--
  if (loadingCount <= 0) {
    loadingCount = 0
    if (loadingInstance) {
      loadingInstance.close()
      loadingInstance = null
    }
  }
}

// 请求拦截器
service.interceptors.request.use(
  (config: any) => {
    const userStore = useUserStore()
    const appStore = useAppStore()

    // 显示加载动画
    if (config.showLoading !== false) {
      showLoading(config.loadingText)
      appStore.setLoading(true)
    }

    // 添加认证token
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 添加请求ID
    config.headers['X-Request-ID'] = generateRequestId()

    // 添加时间戳防止缓存
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now()
      }
    }

    // 添加语言标识
    config.headers['Accept-Language'] = appStore.language

    // 添加用户代理
    config.headers['X-User-Agent'] = navigator.userAgent

    console.log(`[Request] ${config.method?.toUpperCase()} ${config.url}`, config)
    return config
  },
  (error: AxiosError) => {
    hideLoading()
    const appStore = useAppStore()
    appStore.setLoading(false)
    
    console.error('[Request Error]', error)
    ElMessage.error('请求配置错误')
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    hideLoading()
    const appStore = useAppStore()
    appStore.setLoading(false)

    const { data, config } = response
    const requestConfig = config as RequestConfig

    console.log(`[Response] ${config.method?.toUpperCase()} ${config.url}`, data)

    // 检查业务状态码
    if (data.success === false) {
      const errorMessage = data.message || '请求失败'
      
      // 显示错误消息
      if (requestConfig.showError !== false) {
        ElMessage.error(requestConfig.errorMessage || errorMessage)
      }
      
      return Promise.reject(new Error(errorMessage))
    }

    // 显示成功消息
    if (requestConfig.showSuccess && requestConfig.successMessage) {
      ElMessage.success(requestConfig.successMessage)
    }

    return data
  },
  async (error: AxiosError<ApiResponse>) => {
    hideLoading()
    const appStore = useAppStore()
    appStore.setLoading(false)

    const { response, config } = error
    const requestConfig = config as RequestConfig

    console.error(`[Response Error] ${config?.method?.toUpperCase()} ${config?.url}`, error)

    // 处理网络错误
    if (!response) {
      const message = '网络连接失败，请检查网络设置'
      if (requestConfig?.showError !== false) {
        ElMessage.error(message)
      }
      return Promise.reject(new Error(message))
    }

    const { status, data } = response
    let message = data?.message || getErrorMessage(status)

    // 处理不同状态码
    switch (status) {
      case 401:
        await handleUnauthorized()
        break
      case 403:
        message = '权限不足，无法访问该资源'
        break
      case 404:
        message = '请求的资源不存在'
        break
      case 422:
        message = '请求参数验证失败'
        if (data?.errors) {
          handleValidationErrors(data.errors)
          return Promise.reject(error)
        }
        break
      case 429:
        message = '请求过于频繁，请稍后再试'
        break
      case 500:
        message = '服务器内部错误'
        break
      case 502:
        message = '网关错误'
        break
      case 503:
        message = '服务暂时不可用'
        break
      case 504:
        message = '网关超时'
        break
    }

    // 显示错误消息
    if (requestConfig?.showError !== false) {
      ElMessage.error(requestConfig?.errorMessage || message)
    }

    // 重试机制
    if (requestConfig?.retries && requestConfig.retries > 0) {
      return retryRequest(error, requestConfig)
    }

    return Promise.reject(error)
  }
)

// 处理未授权
const handleUnauthorized = async () => {
  const userStore = useUserStore()
  
  try {
    await ElMessageBox.confirm(
      '登录状态已过期，请重新登录',
      '系统提示',
      {
        confirmButtonText: '重新登录',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 清除用户信息
    userStore.resetToken()
    removeToken()
    
    // 跳转到登录页
    router.push({
      path: '/login',
      query: {
        redirect: router.currentRoute.value.fullPath
      }
    })
  } catch {
    // 用户取消，不做处理
  }
}

// 处理验证错误
const handleValidationErrors = (errors: any[]) => {
  const messages = errors.map(error => `${error.field}: ${error.message}`)
  ElMessage.error(messages.join('\n'))
}

// 重试请求
const retryRequest = async (error: AxiosError, config: RequestConfig) => {
  const { retries = 0, retryDelay = 1000 } = config
  
  if (retries > 0) {
    config.retries = retries - 1
    
    // 延迟重试
    await new Promise(resolve => setTimeout(resolve, retryDelay))
    
    return service.request(config)
  }
  
  return Promise.reject(error)
}

// 获取错误消息
const getErrorMessage = (status: number): string => {
  const messages: Record<number, string> = {
    400: '请求参数错误',
    401: '未授权，请重新登录',
    403: '权限不足',
    404: '请求的资源不存在',
    405: '请求方法不允许',
    408: '请求超时',
    409: '请求冲突',
    410: '请求的资源已被删除',
    422: '请求参数验证失败',
    429: '请求过于频繁',
    500: '服务器内部错误',
    501: '服务未实现',
    502: '网关错误',
    503: '服务不可用',
    504: '网关超时',
    505: 'HTTP版本不受支持'
  }
  
  return messages[status] || `请求失败 (${status})`
}

// 生成请求ID
const generateRequestId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// 请求方法封装
class Request {
  // GET请求
  static get<T = any>(
    url: string,
    params?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return service.get(url, {
      params,
      ...config
    })
  }

  // POST请求
  static post<T = any>(
    url: string,
    data?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return service.post(url, data, config)
  }

  // PUT请求
  static put<T = any>(
    url: string,
    data?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return service.put(url, data, config)
  }

  // PATCH请求
  static patch<T = any>(
    url: string,
    data?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return service.patch(url, data, config)
  }

  // DELETE请求
  static delete<T = any>(
    url: string,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return service.delete(url, config)
  }

  // 上传文件
  static upload<T = any>(
    url: string,
    file: File | FormData,
    config?: RequestConfig & {
      onUploadProgress?: (progressEvent: any) => void
    }
  ): Promise<ApiResponse<T>> {
    const formData = file instanceof FormData ? file : new FormData()
    if (file instanceof File) {
      formData.append('file', file)
    }

    return service.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      ...config
    })
  }

  // 下载文件
  static download(
    url: string,
    params?: any,
    filename?: string,
    config?: RequestConfig
  ): Promise<void> {
    return service.get(url, {
      params,
      responseType: 'blob',
      ...config
    }).then((response: any) => {
      const blob = new Blob([response.data])
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename || 'download'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    })
  }

  // 取消请求
  static cancelToken() {
    return axios.CancelToken.source()
  }

  // 判断是否取消请求
  static isCancel(error: any): boolean {
    return axios.isCancel(error)
  }
}

// 导出
export default Request
export { service, type RequestConfig, type ResponseConfig }