/**
 * API 接口主入口文件
 * 统一导出所有 API 模块
 */

// 导出所有 API 模块
export * from './user'
export * from './knowledge'

// 通用 API 配置和工具
export { service as request } from '@/utils/request'

// API 管理器类型
export interface ApiManagerConfig {
  baseURL: string
  timeout: number
  retries: number
  retryDelay: number
  enableCache: boolean
  enableMock: boolean
  enableLogging: boolean
  enableMetrics: boolean
  headers: Record<string, string>
  interceptors: {
    request: Function[]
    response: Function[]
    error: Function[]
  }
}

export interface ApiManagerState {
  initialized: boolean
  config: ApiManagerConfig
  clients: Map<string, any>
  cache: Map<string, any>
  metrics: {
    requests: number
    errors: number
    responseTime: number
    cacheHits: number
  }
  errors: any[]
}

// API 管理器
export class ApiManager {
  private static instance: ApiManager
  private state: ApiManagerState
  private listeners: Map<string, Function[]>

  private constructor() {
    this.state = {
      initialized: false,
      config: this.getDefaultConfig(),
      clients: new Map(),
      cache: new Map(),
      metrics: {
        requests: 0,
        errors: 0,
        responseTime: 0,
        cacheHits: 0
      },
      errors: []
    }
    this.listeners = new Map()
  }

  static getInstance(): ApiManager {
    if (!ApiManager.instance) {
      ApiManager.instance = new ApiManager()
    }
    return ApiManager.instance
  }

  private getDefaultConfig(): ApiManagerConfig {
    return {
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      timeout: 30000,
      retries: 3,
      retryDelay: 1000,
      enableCache: true,
      enableMock: import.meta.env.DEV,
      enableLogging: import.meta.env.DEV,
      enableMetrics: true,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      interceptors: {
        request: [],
        response: [],
        error: []
      }
    }
  }

  // 初始化
  init(config?: Partial<ApiManagerConfig>): void {
    if (this.state.initialized) {
      console.warn('ApiManager already initialized')
      return
    }

    if (config) {
      this.state.config = { ...this.state.config, ...config }
    }

    this.state.initialized = true
    this.emit('initialized', this.state.config)
  }

  // 获取配置
  getConfig(): ApiManagerConfig {
    return { ...this.state.config }
  }

  // 更新配置
  updateConfig(config: Partial<ApiManagerConfig>): void {
    this.state.config = { ...this.state.config, ...config }
    this.emit('configUpdated', this.state.config)
  }

  // 缓存管理
  setCache(key: string, data: any, ttl: number = 300000): void {
    if (!this.state.config.enableCache) return
    
    const item = {
      data,
      timestamp: Date.now(),
      ttl
    }
    this.state.cache.set(key, item)
  }

  getCache(key: string): any {
    if (!this.state.config.enableCache) return null
    
    const item = this.state.cache.get(key)
    if (!item) return null
    
    if (Date.now() - item.timestamp > item.ttl) {
      this.state.cache.delete(key)
      return null
    }
    
    this.state.metrics.cacheHits++
    return item.data
  }

  clearCache(): void {
    this.state.cache.clear()
  }

  // 指标管理
  recordRequest(): void {
    this.state.metrics.requests++
  }

  recordError(error: any): void {
    this.state.metrics.errors++
    this.state.errors.push(error)
    this.emit('error', error)
  }

  recordResponseTime(time: number): void {
    this.state.metrics.responseTime = 
      (this.state.metrics.responseTime + time) / 2
  }

  getMetrics() {
    return { ...this.state.metrics }
  }

  resetMetrics(): void {
    this.state.metrics = {
      requests: 0,
      errors: 0,
      responseTime: 0,
      cacheHits: 0
    }
  }

  // 事件系统
  on(event: string, listener: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(listener)
  }

  off(event: string, listener: Function): void {
    const listeners = this.listeners.get(event)
    if (listeners) {
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  emit(event: string, data?: any): void {
    const listeners = this.listeners.get(event)
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(data)
        } catch (error) {
          console.error('Event listener error:', error)
        }
      })
    }
  }

  // 获取状态
  getState(): ApiManagerState {
    return { ...this.state }
  }
}

// API 装饰器
export function withCache(ttl: number = 300000) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value
    const manager = ApiManager.getInstance()

    descriptor.value = async function (...args: any[]) {
      const key = `${target.constructor.name}.${propertyKey}:${JSON.stringify(args)}`
      
      // 尝试从缓存获取
      const cached = manager.getCache(key)
      if (cached !== null) {
        return cached
      }

      // 执行原方法
      const result = await originalMethod.apply(this, args)
      
      // 缓存结果
      manager.setCache(key, result, ttl)
      
      return result
    }

    return descriptor
  }
}

export function withRetry(maxRetries: number = 3, delay: number = 1000) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value
    const manager = ApiManager.getInstance()

    descriptor.value = async function (...args: any[]) {
      let lastError: any
      
      for (let i = 0; i <= maxRetries; i++) {
        try {
          return await originalMethod.apply(this, args)
        } catch (error) {
          lastError = error
          
          if (i === maxRetries) {
            manager.recordError(error)
            throw error
          }
          
          if (delay > 0) {
            await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
          }
        }
      }
    }

    return descriptor
  }
}

export function withMetrics(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
  const originalMethod = descriptor.value
  const manager = ApiManager.getInstance()

  descriptor.value = async function (...args: any[]) {
    const startTime = performance.now()
    manager.recordRequest()

    try {
      const result = await originalMethod.apply(this, args)
      const endTime = performance.now()
      manager.recordResponseTime(endTime - startTime)
      return result
    } catch (error) {
      const endTime = performance.now()
      manager.recordResponseTime(endTime - startTime)
      manager.recordError(error)
      throw error
    }
  }

  return descriptor
}

// API 混入
export const ApiMixin = {
  data() {
    return {
      apiManager: ApiManager.getInstance()
    }
  },
  
  methods: {
    $api: ApiManager.getInstance()
  }
}

// API 插件
export const ApiPlugin = {
  install(app: any, options?: Partial<ApiManagerConfig>) {
    const manager = ApiManager.getInstance()
    manager.init(options)
    
    // 全局属性
    app.config.globalProperties.$api = manager
    
    // 提供注入
    app.provide('api', manager)
  }
}

// 默认导出 API 管理器实例
export const apiManager = ApiManager.getInstance()

/**
 * API 基础配置
 */
export const API_CONFIG = {
  // API 基础路径
  BASE_URL: import.meta.env.VITE_API_BASE_URL || '/api',
  
  // 请求超时时间（毫秒）
  TIMEOUT: 30000,
  
  // 重试次数
  RETRY_COUNT: 3,
  
  // 重试延迟（毫秒）
  RETRY_DELAY: 1000,
  
  // 文件上传大小限制（字节）
  MAX_FILE_SIZE: 100 * 1024 * 1024, // 100MB
  
  // 支持的文件类型
  SUPPORTED_FILE_TYPES: {
    document: ['.pdf', '.doc', '.docx', '.txt', '.md', '.html'],
    image: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
    archive: ['.zip', '.rar', '.7z', '.tar', '.gz'],
    data: ['.json', '.xml', '.csv', '.xlsx', '.xls']
  },
  
  // 分页默认配置
  PAGINATION: {
    DEFAULT_PAGE: 1,
    DEFAULT_PAGE_SIZE: 20,
    MAX_PAGE_SIZE: 100
  },
  
  // 搜索默认配置
  SEARCH: {
    DEFAULT_LIMIT: 10,
    MAX_LIMIT: 100,
    DEFAULT_THRESHOLD: 0.7
  }
}

/**
 * API 响应状态码
 */
export const API_STATUS = {
  SUCCESS: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  METHOD_NOT_ALLOWED: 405,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504
} as const

/**
 * API 错误消息
 */
export const API_MESSAGES = {
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  TIMEOUT_ERROR: '请求超时，请稍后重试',
  SERVER_ERROR: '服务器内部错误，请稍后重试',
  UNAUTHORIZED: '未授权访问，请重新登录',
  FORBIDDEN: '权限不足，无法访问该资源',
  NOT_FOUND: '请求的资源不存在',
  BAD_REQUEST: '请求参数错误',
  CONFLICT: '资源冲突，请刷新后重试',
  TOO_MANY_REQUESTS: '请求过于频繁，请稍后重试',
  VALIDATION_ERROR: '数据验证失败',
  FILE_TOO_LARGE: '文件大小超出限制',
  UNSUPPORTED_FILE_TYPE: '不支持的文件类型',
  UPLOAD_FAILED: '文件上传失败',
  DOWNLOAD_FAILED: '文件下载失败'
} as const

/**
 * 通用 API 工具函数
 */

/**
 * 构建查询参数
 * @param params 参数对象
 * @returns 查询字符串
 */
export const buildQueryString = (params: Record<string, any>): string => {
  const searchParams = new URLSearchParams()
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(item => searchParams.append(key, String(item)))
      } else {
        searchParams.append(key, String(value))
      }
    }
  })
  
  return searchParams.toString()
}

/**
 * 格式化文件大小
 * @param bytes 字节数
 * @returns 格式化后的文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 检查文件类型是否支持
 * @param fileName 文件名
 * @param category 文件类别
 * @returns 是否支持
 */
export const isFileTypeSupported = (fileName: string, category?: keyof typeof API_CONFIG.SUPPORTED_FILE_TYPES): boolean => {
  const extension = '.' + fileName.split('.').pop()?.toLowerCase()
  
  if (category) {
    return API_CONFIG.SUPPORTED_FILE_TYPES[category]?.includes(extension) || false
  }
  
  return Object.values(API_CONFIG.SUPPORTED_FILE_TYPES)
    .flat()
    .includes(extension)
}

/**
 * 检查文件大小是否超出限制
 * @param fileSize 文件大小（字节）
 * @returns 是否超出限制
 */
export const isFileSizeExceeded = (fileSize: number): boolean => {
  return fileSize > API_CONFIG.MAX_FILE_SIZE
}

/**
 * 创建分页参数
 * @param page 页码
 * @param pageSize 每页大小
 * @returns 分页参数
 */
export const createPaginationParams = (page?: number, pageSize?: number) => {
  return {
    page: page || API_CONFIG.PAGINATION.DEFAULT_PAGE,
    pageSize: Math.min(
      pageSize || API_CONFIG.PAGINATION.DEFAULT_PAGE_SIZE,
      API_CONFIG.PAGINATION.MAX_PAGE_SIZE
    )
  }
}

/**
 * 创建搜索参数
 * @param query 搜索关键词
 * @param options 搜索选项
 * @returns 搜索参数
 */
export const createSearchParams = (
  query: string,
  options: {
    limit?: number
    threshold?: number
    filters?: Record<string, any>
  } = {}
) => {
  return {
    query,
    limit: Math.min(
      options.limit || API_CONFIG.SEARCH.DEFAULT_LIMIT,
      API_CONFIG.SEARCH.MAX_LIMIT
    ),
    threshold: options.threshold || API_CONFIG.SEARCH.DEFAULT_THRESHOLD,
    ...options.filters
  }
}

/**
 * API 响应处理器
 */
export class ApiResponseHandler {
  /**
   * 处理成功响应
   * @param response 响应数据
   * @returns 处理后的数据
   */
  static handleSuccess<T>(response: any): T {
    return response.data || response
  }
  
  /**
   * 处理错误响应
   * @param error 错误对象
   * @returns 错误信息
   */
  static handleError(error: any): string {
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case API_STATUS.BAD_REQUEST:
          return data?.message || API_MESSAGES.BAD_REQUEST
        case API_STATUS.UNAUTHORIZED:
          return API_MESSAGES.UNAUTHORIZED
        case API_STATUS.FORBIDDEN:
          return API_MESSAGES.FORBIDDEN
        case API_STATUS.NOT_FOUND:
          return API_MESSAGES.NOT_FOUND
        case API_STATUS.CONFLICT:
          return API_MESSAGES.CONFLICT
        case API_STATUS.UNPROCESSABLE_ENTITY:
          return data?.message || API_MESSAGES.VALIDATION_ERROR
        case API_STATUS.TOO_MANY_REQUESTS:
          return API_MESSAGES.TOO_MANY_REQUESTS
        case API_STATUS.INTERNAL_SERVER_ERROR:
          return API_MESSAGES.SERVER_ERROR
        default:
          return data?.message || API_MESSAGES.SERVER_ERROR
      }
    } else if (error.request) {
      return API_MESSAGES.NETWORK_ERROR
    } else if (error.code === 'ECONNABORTED') {
      return API_MESSAGES.TIMEOUT_ERROR
    } else {
      return error.message || API_MESSAGES.SERVER_ERROR
    }
  }
  
  /**
   * 处理分页响应
   * @param response 分页响应
   * @returns 处理后的分页数据
   */
  static handlePaginatedResponse<T>(response: any): {
    data: T[]
    total: number
    page: number
    pageSize: number
    totalPages: number
  } {
    const { data, total, page, pageSize } = response
    
    return {
      data: data || [],
      total: total || 0,
      page: page || 1,
      pageSize: pageSize || API_CONFIG.PAGINATION.DEFAULT_PAGE_SIZE,
      totalPages: Math.ceil((total || 0) / (pageSize || API_CONFIG.PAGINATION.DEFAULT_PAGE_SIZE))
    }
  }
}

/**
 * API 缓存管理器
 */
export class ApiCacheManager {
  private static cache = new Map<string, { data: any; timestamp: number; ttl: number }>()
  
  /**
   * 设置缓存
   * @param key 缓存键
   * @param data 缓存数据
   * @param ttl 生存时间（毫秒）
   */
  static set(key: string, data: any, ttl: number = 5 * 60 * 1000): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    })
  }
  
  /**
   * 获取缓存
   * @param key 缓存键
   * @returns 缓存数据或 null
   */
  static get(key: string): any | null {
    const cached = this.cache.get(key)
    
    if (!cached) {
      return null
    }
    
    if (Date.now() - cached.timestamp > cached.ttl) {
      this.cache.delete(key)
      return null
    }
    
    return cached.data
  }
  
  /**
   * 删除缓存
   * @param key 缓存键
   */
  static delete(key: string): void {
    this.cache.delete(key)
  }
  
  /**
   * 清空所有缓存
   */
  static clear(): void {
    this.cache.clear()
  }
  
  /**
   * 清理过期缓存
   */
  static cleanup(): void {
    const now = Date.now()
    
    for (const [key, cached] of this.cache.entries()) {
      if (now - cached.timestamp > cached.ttl) {
        this.cache.delete(key)
      }
    }
  }
}

// 定期清理过期缓存
setInterval(() => {
  ApiCacheManager.cleanup()
}, 10 * 60 * 1000) // 每10分钟清理一次

/**
 * API 请求拦截器
 */
export const setupApiInterceptors = () => {
  // 这里可以添加全局的请求和响应拦截器
  // 例如：添加认证头、处理错误等
}

/**
 * 导出默认配置
 */
export default {
  API_CONFIG,
  API_STATUS,
  API_MESSAGES,
  ApiResponseHandler,
  ApiCacheManager,
  buildQueryString,
  formatFileSize,
  isFileTypeSupported,
  isFileSizeExceeded,
  createPaginationParams,
  createSearchParams,
  setupApiInterceptors
}