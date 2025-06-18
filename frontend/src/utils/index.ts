/**
 * 工具函数主入口文件
 */

// 只导出实际存在的模块中的函数

// 重新导出实际存在的模块中的函数
export {
  // 请求相关
  service as request
} from './request'

export {
  // 认证相关
  getToken,
  setToken,
  removeToken,
  getRefreshToken,
  setRefreshToken,
  removeRefreshToken,
  getUserInfo,
  setUserInfo,
  removeUserInfo,
  getPermissions,
  setPermissions,
  removePermissions,
  hasPermission,
  hasRole,
  isTokenExpired,
  getTokenRemainingTime,
  parseJWT
} from './auth'

export {
  // 加密相关
  encrypt,
  decrypt,
  md5,
  sha256,
  sha512,
  base64Encode,
  base64Decode,
  base64UrlEncode,
  base64UrlDecode,
  generateRandomString,
  generateUUID,
  hmacSha256,
  verifyHmacSha256,
  checkPasswordStrength,
  generateSecurePassword,
  calculateFileHash,
  verifyDataIntegrity,
  maskSensitiveInfo
} from './crypto'

export {
  // 通用工具
  formatRelativeTime,
  generateRandomColor,
  getContrastColor,
  getUrlParam,
  setUrlParams,
  removeUrlParams,
  getBrowserInfo,
  getOperatingSystem,
  fullscreen,
  message,
  notification,
  confirm,
  uniqueArray,
  groupBy,
  sortBy,
  flattenTree,
  arrayToTree
} from './common'

// 验证相关函数已在上面导出，避免重复导出

export {
  // 存储相关
  localStorage,
  sessionStorage,
  userStorage
} from './storage'

// 导出类型
export type {
  // 请求相关类型
  RequestConfig
} from './request'

// 定义拦截器类型
export interface RequestInterceptor {
  onFulfilled?: (config: any) => any
  onRejected?: (error: any) => any
}

export interface ResponseInterceptor {
  onFulfilled?: (response: any) => any
  onRejected?: (error: any) => any
}

// 定义缺失的类型
export interface UtilsUploadConfig {
  url: string
  method?: 'POST' | 'PUT'
  headers?: Record<string, string>
  data?: FormData | Record<string, any>
  timeout?: number
  onProgress?: UploadProgressCallback
}

export type UploadProgressCallback = (progress: {
  loaded: number
  total: number
  percentage: number
}) => void

export interface DownloadConfig {
  url: string
  filename?: string
  headers?: Record<string, string>
  timeout?: number
}

export interface TokenInfo {
  access_token: string
  refresh_token?: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: string
  username: string
  email: string
  avatar?: string
  roles: string[]
  permissions: string[]
}

export interface Permission {
  id: string
  name: string
  code: string
  description?: string
}

export interface Role {
  id: string
  name: string
  code: string
  description?: string
  permissions: Permission[]
}

export type {
  // 验证相关类型
  CustomValidator,
  AsyncValidator
} from './validate'

export type {
  // 存储相关类型
  StorageType,
  StorageOptions,
  StorageEvent
} from './storage'

/**
 * 工具函数版本信息
 */
export const UTILS_VERSION = '1.0.0'

/**
 * 工具函数配置
 */
export interface UtilsConfig {
  /** 请求基础URL */
  baseURL?: string
  /** 请求超时时间 */
  timeout?: number
  /** 存储前缀 */
  storagePrefix?: string
  /** 加密密钥 */
  secretKey?: string
  /** 是否启用调试模式 */
  debug?: boolean
}

/**
 * 默认配置
 */
const defaultConfig: UtilsConfig = {
  baseURL: '/api',
  timeout: 10000,
  storagePrefix: 'app_',
  secretKey: 'default-secret-key',
  debug: import.meta.env.DEV
}

/**
 * 当前配置
 */
let currentConfig: UtilsConfig = { ...defaultConfig }

/**
 * 配置工具函数
 * @param config 配置选项
 */
export const configureUtils = (config: Partial<UtilsConfig>): void => {
  currentConfig = { ...currentConfig, ...config }
  
  // 这里可以根据配置更新各个工具模块的设置
  if (config.debug !== undefined) {
    // 设置调试模式
    console.log('Utils debug mode:', config.debug)
  }
}

/**
 * 获取当前配置
 * @returns 当前配置
 */
export const getUtilsConfig = (): UtilsConfig => {
  return { ...currentConfig }
}

/**
 * 重置配置为默认值
 */
export const resetUtilsConfig = (): void => {
  currentConfig = { ...defaultConfig }
}

/**
 * 工具函数初始化
 * @param config 初始化配置
 */
export const initUtils = async (config?: Partial<UtilsConfig>): Promise<void> => {
  if (config) {
    configureUtils(config)
  }
  
  // 执行初始化逻辑
  console.log('Utils initialized with config:', currentConfig)
  
  // 清理过期缓存
  try {
    const { cacheStorage } = await import('./storage')
    cacheStorage.clearExpired()
  } catch (error) {
    console.warn('Failed to clear expired cache:', error)
  }
}

/**
 * 工具函数健康检查
 * @returns 健康检查结果
 */
export const healthCheck = (): {
  status: 'ok' | 'error'
  version: string
  config: UtilsConfig
  storage: {
    localStorage: boolean
    sessionStorage: boolean
  }
  features: {
    crypto: boolean
    clipboard: boolean
    fullscreen: boolean
    notification: boolean
  }
} => {
  const result = {
    status: 'ok' as 'ok' | 'error',
    version: UTILS_VERSION,
    config: currentConfig,
    storage: {
      localStorage: false,
      sessionStorage: false
    },
    features: {
      crypto: false,
      clipboard: false,
      fullscreen: false,
      notification: false
    }
  }

  try {
    // 检查存储功能
    result.storage.localStorage = typeof window !== 'undefined' && !!window.localStorage
    result.storage.sessionStorage = typeof window !== 'undefined' && !!window.sessionStorage

    // 检查各种功能
    result.features.crypto = typeof window !== 'undefined' && !!window.crypto
    result.features.clipboard = typeof navigator !== 'undefined' && !!navigator.clipboard
    result.features.fullscreen = typeof document !== 'undefined' && !!document.fullscreenEnabled
    result.features.notification = typeof window !== 'undefined' && 'Notification' in window
  } catch (error) {
    console.error('Health check failed:', error)
    result.status = 'error' as const
  }

  return result
}

/**
 * 工具函数使用统计
 */
export class UtilsStats {
  private static instance: UtilsStats
  private stats: Map<string, number> = new Map()

  static getInstance(): UtilsStats {
    if (!UtilsStats.instance) {
      UtilsStats.instance = new UtilsStats()
    }
    return UtilsStats.instance
  }

  /**
   * 记录函数调用
   * @param functionName 函数名
   */
  record(functionName: string): void {
    const count = this.stats.get(functionName) || 0
    this.stats.set(functionName, count + 1)
  }

  /**
   * 获取统计信息
   * @returns 统计信息
   */
  getStats(): Record<string, number> {
    return Object.fromEntries(this.stats)
  }

  /**
   * 获取最常用的函数
   * @param limit 返回数量限制
   * @returns 最常用的函数列表
   */
  getTopUsed(limit = 10): Array<{ name: string; count: number }> {
    return Array.from(this.stats.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit)
  }

  /**
   * 重置统计信息
   */
  reset(): void {
    this.stats.clear()
  }

  /**
   * 导出统计信息
   * @returns JSON字符串
   */
  export(): string {
    return JSON.stringify({
      timestamp: Date.now(),
      stats: this.getStats(),
      topUsed: this.getTopUsed()
    }, null, 2)
  }
}

/**
 * 默认的统计实例
 */
export const utilsStats = UtilsStats.getInstance()

/**
 * 创建带统计的函数包装器
 * @param functionName 函数名
 * @param fn 原函数
 * @returns 包装后的函数
 */
export const withStats = <T extends (...args: any[]) => any>(
  functionName: string,
  fn: T
): T => {
  return ((...args: any[]) => {
    utilsStats.record(functionName)
    return fn(...args)
  }) as T
}

/**
 * 工具函数调试器
 */
export class UtilsDebugger {
  private static instance: UtilsDebugger
  private logs: Array<{
    timestamp: number
    level: 'info' | 'warn' | 'error'
    message: string
    data?: any
  }> = []
  private maxLogs = 1000

  static getInstance(): UtilsDebugger {
    if (!UtilsDebugger.instance) {
      UtilsDebugger.instance = new UtilsDebugger()
    }
    return UtilsDebugger.instance
  }

  /**
   * 记录日志
   * @param level 日志级别
   * @param message 消息
   * @param data 附加数据
   */
  log(level: 'info' | 'warn' | 'error', message: string, data?: any): void {
    if (!currentConfig.debug) return

    const logEntry = {
      timestamp: Date.now(),
      level,
      message,
      data
    }

    this.logs.push(logEntry)

    // 限制日志数量
    if (this.logs.length > this.maxLogs) {
      this.logs.shift()
    }

    // 输出到控制台
    const consoleMethod = level === 'error' ? console.error : 
                         level === 'warn' ? console.warn : console.log
    consoleMethod(`[Utils ${level.toUpperCase()}] ${message}`, data || '')
  }

  /**
   * 获取日志
   * @param level 过滤级别
   * @returns 日志列表
   */
  getLogs(level?: 'info' | 'warn' | 'error') {
    if (level) {
      return this.logs.filter(log => log.level === level)
    }
    return [...this.logs]
  }

  /**
   * 清空日志
   */
  clear(): void {
    this.logs = []
  }

  /**
   * 导出日志
   * @returns JSON字符串
   */
  export(): string {
    return JSON.stringify({
      timestamp: Date.now(),
      logs: this.logs
    }, null, 2)
  }
}

/**
 * 默认的调试器实例
 */
export const utilsDebugger = UtilsDebugger.getInstance()

/**
 * 便捷的调试函数
 */
export const debug = {
  info: (message: string, data?: any) => utilsDebugger.log('info', message, data),
  warn: (message: string, data?: any) => utilsDebugger.log('warn', message, data),
  error: (message: string, data?: any) => utilsDebugger.log('error', message, data)
}

// 工具函数注册表接口
export interface UtilsRegistry {
  functions: Map<string, Function>
  categories: Map<string, string[]>
  aliases: Map<string, string>
  metadata: Map<string, UtilFunctionMetadata>
}

// 工具函数元数据
export interface UtilFunctionMetadata {
  name: string
  category: string
  description: string
  version: string
  author?: string
  tags?: string[]
  dependencies?: string[]
  examples?: string[]
  performance?: {
    complexity: string
    memory: string
    benchmark?: number
  }
  compatibility?: {
    browsers?: string[]
    node?: string
    typescript?: boolean
  }
}

// 工具函数管理器配置
export interface UtilsManagerConfig extends UtilsConfig {
  autoRegister?: boolean
  enableValidation?: boolean
  enableCaching?: boolean
  enableProfiling?: boolean
  enableMetrics?: boolean
}

// 工具函数管理器类
export class UtilsManager {
  private static instance: UtilsManager
  private registry: UtilsRegistry
  private config: UtilsManagerConfig
  private cache = new Map<string, any>()
  private metrics = new Map<string, { calls: number, totalTime: number, errors: number }>()
  private eventListeners = new Map<string, Function[]>()
  private initialized = false

  private constructor(config: UtilsManagerConfig = {}) {
    this.config = {
      debug: false,
      baseURL: '/api',
      timeout: 10000,
      storagePrefix: 'app_',
      secretKey: 'default-secret-key',
      autoRegister: true,
      enableValidation: true,
      enableCaching: true,
      enableProfiling: false,
      enableMetrics: true,
      ...config
    }

    this.registry = {
      functions: new Map(),
      categories: new Map(),
      aliases: new Map(),
      metadata: new Map()
    }
  }

  // 获取单例实例
  static getInstance(config?: UtilsManagerConfig): UtilsManager {
    if (!UtilsManager.instance) {
      UtilsManager.instance = new UtilsManager(config)
    }
    return UtilsManager.instance
  }

  // 初始化工具管理器
  initialize(): void {
    if (this.initialized) {
      console.warn('UtilsManager already initialized')
      return
    }

    this.initialized = true

    // 自动注册内置工具函数
    if (this.config.autoRegister) {
      this.registerBuiltinUtils()
    }

    // 触发初始化事件
    this.emit('initialized', this)

    if (this.config.debug) {
      console.log('UtilsManager initialized successfully')
    }
  }

  // 注册工具函数
  registerFunction(
    name: string,
    fn: Function,
    metadata: Partial<UtilFunctionMetadata> = {}
  ): void {
    // 验证函数
    if (this.config.enableValidation && !this.validateFunction(fn)) {
      throw new Error(`Invalid function: ${name}`)
    }

    // 包装函数以添加监控
    const wrappedFn = this.wrapFunction(name, fn)

    // 存储到注册表
    this.registry.functions.set(name, wrappedFn)

    // 存储元数据
    const fullMetadata: UtilFunctionMetadata = {
      name,
      category: 'general',
      description: '',
      version: '1.0.0',
      ...metadata
    }
    this.registry.metadata.set(name, fullMetadata)

    // 按类别分组
    const category = fullMetadata.category
    if (!this.registry.categories.has(category)) {
      this.registry.categories.set(category, [])
    }
    this.registry.categories.get(category)!.push(name)

    // 初始化指标
    if (this.config.enableMetrics) {
      this.metrics.set(name, { calls: 0, totalTime: 0, errors: 0 })
    }

    // 触发注册事件
    this.emit('function:registered', { name, metadata: fullMetadata })

    if (this.config.debug) {
      console.log(`Function registered: ${name}`)
    }
  }

  // 批量注册工具函数
  registerFunctions(functions: Record<string, { fn: Function, metadata?: Partial<UtilFunctionMetadata> }>): void {
    Object.entries(functions).forEach(([name, { fn, metadata }]) => {
      this.registerFunction(name, fn, metadata)
    })
  }

  // 注册函数别名
  registerAlias(alias: string, originalName: string): void {
    if (!this.registry.functions.has(originalName)) {
      throw new Error(`Function not found: ${originalName}`)
    }

    this.registry.aliases.set(alias, originalName)
    this.registry.functions.set(alias, this.registry.functions.get(originalName)!)

    if (this.config.debug) {
      console.log(`Alias registered: ${alias} -> ${originalName}`)
    }
  }

  // 获取工具函数
  getFunction(name: string): Function | undefined {
    // 检查别名
    const actualName = this.registry.aliases.get(name) || name
    return this.registry.functions.get(actualName)
  }

  // 调用工具函数
  call(name: string, ...args: any[]): any {
    const fn = this.getFunction(name)
    if (!fn) {
      throw new Error(`Function not found: ${name}`)
    }

    return fn(...args)
  }

  // 异步调用工具函数
  async callAsync(name: string, ...args: any[]): Promise<any> {
    const fn = this.getFunction(name)
    if (!fn) {
      throw new Error(`Function not found: ${name}`)
    }

    return await fn(...args)
  }

  // 包装函数以添加监控
  private wrapFunction(name: string, fn: Function): Function {
    return (...args: any[]) => {
      const startTime = performance.now()
      
      try {
        // 更新调用次数
        if (this.config.enableMetrics) {
          const metrics = this.metrics.get(name)!
          metrics.calls++
        }

        // 执行函数
        const result = fn(...args)

        // 处理 Promise
        if (result instanceof Promise) {
          return result.catch(error => {
            this.handleError(name, error)
            throw error
          }).finally(() => {
            this.updateMetrics(name, startTime)
          })
        }

        // 更新指标
        this.updateMetrics(name, startTime)

        return result
      } catch (error) {
        this.handleError(name, error)
        this.updateMetrics(name, startTime)
        throw error
      }
    }
  }

  // 更新指标
  private updateMetrics(name: string, startTime: number): void {
    if (!this.config.enableMetrics) return

    const metrics = this.metrics.get(name)
    if (metrics) {
      const duration = performance.now() - startTime
      metrics.totalTime += duration
    }
  }

  // 处理错误
  private handleError(name: string, error: any): void {
    if (this.config.enableMetrics) {
      const metrics = this.metrics.get(name)
      if (metrics) {
        metrics.errors++
      }
    }

    // 触发错误事件
    this.emit('function:error', { name, error })

    if (this.config.debug) {
      console.error(`Error in function ${name}:`, error)
    }
  }

  // 验证函数
  private validateFunction(fn: Function): boolean {
    return typeof fn === 'function'
  }

  // 获取所有函数
  getAllFunctions(): string[] {
    return Array.from(this.registry.functions.keys())
  }

  // 按类别获取函数
  getFunctionsByCategory(category: string): string[] {
    return this.registry.categories.get(category) || []
  }

  // 获取所有类别
  getAllCategories(): string[] {
    return Array.from(this.registry.categories.keys())
  }

  // 搜索函数
  searchFunctions(query: string): string[] {
    const lowerQuery = query.toLowerCase()
    return this.getAllFunctions().filter(name => {
      const metadata = this.registry.metadata.get(name)
      return (
        name.toLowerCase().includes(lowerQuery) ||
        metadata?.description.toLowerCase().includes(lowerQuery) ||
        metadata?.tags?.some(tag => tag.toLowerCase().includes(lowerQuery))
      )
    })
  }

  // 获取函数元数据
  getFunctionMetadata(name: string): UtilFunctionMetadata | undefined {
    const actualName = this.registry.aliases.get(name) || name
    return this.registry.metadata.get(actualName)
  }

  // 获取函数指标
  getFunctionMetrics(name: string): { calls: number, totalTime: number, errors: number, avgTime: number } | undefined {
    const actualName = this.registry.aliases.get(name) || name
    const metrics = this.metrics.get(actualName)
    
    if (!metrics) return undefined

    return {
      ...metrics,
      avgTime: metrics.calls > 0 ? metrics.totalTime / metrics.calls : 0
    }
  }

  // 获取所有指标
  getAllMetrics(): Record<string, { calls: number, totalTime: number, errors: number, avgTime: number }> {
    const result: Record<string, any> = {}
    
    this.metrics.forEach((metrics, name) => {
      result[name] = {
        ...metrics,
        avgTime: metrics.calls > 0 ? metrics.totalTime / metrics.calls : 0
      }
    })

    return result
  }

  // 清除缓存
  clearCache(): void {
    this.cache.clear()
    this.emit('cache:cleared')
  }

  // 重置指标
  resetMetrics(): void {
    this.metrics.forEach(metrics => {
      metrics.calls = 0
      metrics.totalTime = 0
      metrics.errors = 0
    })
    this.emit('metrics:reset')
  }

  // 事件系统
  on(event: string, listener: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event)!.push(listener)
  }

  off(event: string, listener?: Function): void {
    if (!this.eventListeners.has(event)) return
    
    if (listener) {
      const listeners = this.eventListeners.get(event)!
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    } else {
      this.eventListeners.delete(event)
    }
  }

  emit(event: string, data?: any): void {
    if (!this.eventListeners.has(event)) return
    
    this.eventListeners.get(event)!.forEach(listener => {
      try {
        listener(data)
      } catch (error) {
        console.error(`Error in event listener for ${event}:`, error)
      }
    })
  }

  // 获取配置
  getConfig(): UtilsManagerConfig {
    return { ...this.config }
  }

  // 更新配置
  updateConfig(config: Partial<UtilsManagerConfig>): void {
    this.config = { ...this.config, ...config }
    this.emit('config:updated', this.config)
  }

  // 获取注册表信息
  getRegistryInfo(): {
    totalFunctions: number
    totalCategories: number
    totalAliases: number
    functionsByCategory: Record<string, number>
  } {
    const functionsByCategory: Record<string, number> = {}
    this.registry.categories.forEach((functions, category) => {
      functionsByCategory[category] = functions.length
    })

    return {
      totalFunctions: this.registry.functions.size,
      totalCategories: this.registry.categories.size,
      totalAliases: this.registry.aliases.size,
      functionsByCategory
    }
  }

  // 注册内置工具函数
  private registerBuiltinUtils(): void {
    // 注册一些基础工具函数
    this.registerFunction('noop', () => {}, {
      category: 'common',
      description: 'No operation function',
      tags: ['utility', 'common']
    })

    this.registerFunction('identity', (value: any) => value, {
      category: 'common',
      description: 'Returns the first argument it receives',
      tags: ['utility', 'common']
    })

    this.registerFunction('isFunction', (value: any) => typeof value === 'function', {
      category: 'type',
      description: 'Checks if value is a function',
      tags: ['type', 'check']
    })

    this.registerFunction('isObject', (value: any) => value !== null && typeof value === 'object', {
      category: 'type',
      description: 'Checks if value is an object',
      tags: ['type', 'check']
    })

    this.registerFunction('isArray', Array.isArray, {
      category: 'type',
      description: 'Checks if value is an array',
      tags: ['type', 'check', 'array']
    })

    this.registerFunction('isString', (value: any) => typeof value === 'string', {
      category: 'type',
      description: 'Checks if value is a string',
      tags: ['type', 'check', 'string']
    })

    this.registerFunction('isNumber', (value: any) => typeof value === 'number' && !isNaN(value), {
      category: 'type',
      description: 'Checks if value is a number',
      tags: ['type', 'check', 'number']
    })

    this.registerFunction('isBoolean', (value: any) => typeof value === 'boolean', {
      category: 'type',
      description: 'Checks if value is a boolean',
      tags: ['type', 'check', 'boolean']
    })

    this.registerFunction('isEmpty', (value: any) => {
      if (value == null) return true
      if (Array.isArray(value) || typeof value === 'string') return value.length === 0
      if (typeof value === 'object') return Object.keys(value).length === 0
      return false
    }, {
      category: 'type',
      description: 'Checks if value is empty',
      tags: ['type', 'check', 'empty']
    })

    this.registerFunction('clone', (value: any) => {
      if (value === null || typeof value !== 'object') return value
      if (value instanceof Date) return new Date(value.getTime())
      if (Array.isArray(value)) return value.map(item => this.call('clone', item))
      if (typeof value === 'object') {
        const cloned: any = {}
        Object.keys(value).forEach(key => {
          cloned[key] = this.call('clone', value[key])
        })
        return cloned
      }
      return value
    }, {
      category: 'object',
      description: 'Creates a deep clone of value',
      tags: ['object', 'clone', 'deep']
    })
  }

  // 清除注册表
  clearRegistry(): void {
    this.registry.functions.clear()
    this.registry.categories.clear()
    this.registry.aliases.clear()
    this.registry.metadata.clear()
    this.metrics.clear()
    this.cache.clear()
    this.emit('registry:cleared')
  }

  // 重置管理器
  reset(): void {
    this.clearRegistry()
    this.eventListeners.clear()
    this.initialized = false
    this.emit('reset')
  }

  // 销毁管理器
  destroy(): void {
    this.reset()
    UtilsManager.instance = null as any
  }
}

// 工具函数装饰器
export function Util(metadata: Partial<UtilFunctionMetadata> = {}) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const manager = UtilsManager.getInstance()
    const fn = descriptor.value
    
    if (typeof fn === 'function') {
      manager.registerFunction(propertyKey, fn, {
        name: propertyKey,
        ...metadata
      })
    }
    
    return descriptor
  }
}

// 类别装饰器
export function Category(category: string) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const manager = UtilsManager.getInstance()
    const metadata = manager.getFunctionMetadata(propertyKey)
    
    if (metadata) {
      metadata.category = category
    }
    
    return descriptor
  }
}

// 标签装饰器
export function Tags(...tags: string[]) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const manager = UtilsManager.getInstance()
    const metadata = manager.getFunctionMetadata(propertyKey)
    
    if (metadata) {
      metadata.tags = tags
    }
    
    return descriptor
  }
}

// 工具函数常量
export const UTILS_CONSTANTS = {
  // 类别
  CATEGORIES: {
    COMMON: 'common',
    TYPE: 'type',
    OBJECT: 'object',
    ARRAY: 'array',
    STRING: 'string',
    NUMBER: 'number',
    DATE: 'date',
    FUNCTION: 'function',
    ASYNC: 'async',
    DOM: 'dom',
    EVENT: 'event',
    STORAGE: 'storage',
    NETWORK: 'network',
    CRYPTO: 'crypto',
    FORMAT: 'format',
    VALIDATE: 'validate',
    PERFORMANCE: 'performance',
    DEBUG: 'debug'
  },
  
  // 事件
  EVENTS: {
    INITIALIZED: 'initialized',
    FUNCTION_REGISTERED: 'function:registered',
    FUNCTION_ERROR: 'function:error',
    CACHE_CLEARED: 'cache:cleared',
    METRICS_RESET: 'metrics:reset',
    CONFIG_UPDATED: 'config:updated',
    CONFIG_IMPORTED: 'config:imported',
    REGISTRY_CLEARED: 'registry:cleared',
    RESET: 'reset'
  },
  
  // 日志级别
  LOG_LEVELS: {
    ERROR: 'error',
    WARN: 'warn',
    INFO: 'info',
    DEBUG: 'debug',
    TRACE: 'trace'
  }
} as const

// 创建工具管理器实例
export const utilsManager = UtilsManager.getInstance()

// 安装工具函数
export function setupUtils(config: UtilsManagerConfig = {}) {
  const manager = UtilsManager.getInstance(config)
  
  // 初始化管理器
  manager.initialize()
  
  // 在开发环境下添加调试信息
  if (import.meta.env.DEV) {
    (window as any).__utilsManager = manager
    console.log('[UtilsManager] Registry Info:', manager.getRegistryInfo())
    console.log('[UtilsManager] All Metrics:', manager.getAllMetrics())
  }
  
  return manager
}

// 导出默认工具管理器
export const defaultUtilsManager = {
  manager: utilsManager,
  setup: setupUtils
}