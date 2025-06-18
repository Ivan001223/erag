// 导出核心业务服务
/**
 * 服务层主入口文件
 * 提供服务管理和基础服务功能
 */

// 基础服务导出
// 注意：其他模块的导出已移除以避免循环依赖和类型错误
// 如需使用 API、工具函数等，请直接从对应模块导入

// 服务配置接口
export interface ServiceConfig {
  // 基础配置
  baseUrl: string
  timeout: number
  retries: number
  
  // API配置
  api: {
    version: string
    endpoints: Record<string, string>
    headers: Record<string, string>
  }
  
  // 认证配置
  auth: {
    type: 'jwt' | 'oauth' | 'basic'
    tokenKey: string
    refreshKey: string
    expireTime: number
  }
  
  // 缓存配置
  cache: {
    enabled: boolean
    ttl: number
    maxSize: number
    strategy: 'lru' | 'fifo' | 'lfu'
  }
  
  // 日志配置
  logging: {
    level: 'debug' | 'info' | 'warn' | 'error'
    enabled: boolean
    maxFiles: number
    maxSize: string
  }
}

// 服务注册表接口
export interface ServiceRegistry {
  services: Map<string, any>
  plugins: Map<string, ServicePlugin>
  middleware: ServiceMiddleware[]
  config: ServiceConfig
  eventBus: EventTarget
  metrics: Map<string, any>
}

// 服务管理器配置接口
export interface ServiceManagerConfig {
  autoStart: boolean
  enableMetrics: boolean
  enableEvents: boolean
  maxRetries: number
  retryDelay: number
}

// 服务插件接口
export interface ServicePlugin {
  name: string
  version: string
  install: (serviceManager: ServiceManager) => void
  uninstall?: (serviceManager: ServiceManager) => void
  dependencies?: string[]
}

// 服务中间件接口
export interface ServiceMiddleware {
  name: string
  priority: number
  execute: (context: any, next: () => Promise<any>) => Promise<any>
}

// 服务管理器类
export class ServiceManager {
  private static instance: ServiceManager
  private registry: ServiceRegistry
  private config: ServiceManagerConfig
  private initialized = false
  private eventBus = new EventTarget()
  private metrics = new Map<string, any>()
  
  private constructor() {
    this.registry = {
      services: new Map(),
      plugins: new Map(),
      middleware: [],
      config: this.createDefaultConfig(),
      eventBus: this.eventBus,
      metrics: this.metrics,
    }
    this.config = {
      autoStart: true,
      enableMetrics: true,
      enableEvents: true,
      maxRetries: 3,
      retryDelay: 1000,
    }
  }
  
  static getInstance(): ServiceManager {
    if (!ServiceManager.instance) {
      ServiceManager.instance = new ServiceManager()
    }
    return ServiceManager.instance
  }
  
  // 初始化服务管理器
  async initialize(config?: Partial<ServiceManagerConfig>): Promise<void> {
    if (this.initialized) return
    
    if (config) {
      this.config = { ...this.config, ...config }
    }
    
    // 初始化内置服务
    await this.initializeBuiltinServices()
    
    // 应用插件
    await this.applyPlugins()
    
    // 应用中间件
    this.applyMiddleware()
    
    this.initialized = true
    this.emit('initialized', { timestamp: Date.now() })
  }
  
  // 注册服务
  registerService<T>(name: string, service: T): void {
    if (this.registry.services.has(name)) {
      throw new Error(`Service '${name}' already registered`)
    }
    
    this.registry.services.set(name, service)
    this.emit('serviceRegistered', { name, service })
    this.recordMetric('serviceRegistered', name)
  }
  
  // 批量注册服务
  registerServices(services: Record<string, any>): void {
    Object.entries(services).forEach(([name, service]) => {
      this.registerService(name, service)
    })
  }
  
  // 获取服务
  getService<T>(name: string): T {
    const service = this.registry.services.get(name)
    if (!service) {
      throw new Error(`Service '${name}' not found`)
    }
    return service as T
  }
  
  // 注销服务
  unregisterService(name: string): boolean {
    const removed = this.registry.services.delete(name)
    if (removed) {
      this.emit('serviceUnregistered', { name })
      this.recordMetric('serviceUnregistered', name)
    }
    return removed
  }
  
  // 注册插件
  registerPlugin(plugin: ServicePlugin): void {
    if (this.registry.plugins.has(plugin.name)) {
      throw new Error(`Plugin '${plugin.name}' already registered`)
    }
    
    this.registry.plugins.set(plugin.name, plugin)
    plugin.install(this)
    this.emit('pluginRegistered', { plugin })
  }
  
  // 批量注册插件
  registerPlugins(plugins: ServicePlugin[]): void {
    plugins.forEach(plugin => this.registerPlugin(plugin))
  }
  
  // 注册中间件
  registerMiddleware(middleware: ServiceMiddleware): void {
    this.registry.middleware.push(middleware)
    // 按优先级排序
    this.registry.middleware.sort((a, b) => b.priority - a.priority)
    this.emit('middlewareRegistered', { middleware })
  }
  
  // 批量注册中间件
  registerMiddlewares(middlewares: ServiceMiddleware[]): void {
    middlewares.forEach(middleware => this.registerMiddleware(middleware))
  }
  
  // 事件发射器
  emit(event: string, data?: any): void {
    if (this.config.enableEvents) {
      this.eventBus.dispatchEvent(new CustomEvent(event, { detail: data }))
    }
  }
  
  // 事件监听器
  on(event: string, listener: EventListener): void {
    this.eventBus.addEventListener(event, listener)
  }
  
  // 移除事件监听器
  off(event: string, listener: EventListener): void {
    this.eventBus.removeEventListener(event, listener)
  }
  
  // 初始化内置服务
  private async initializeBuiltinServices(): Promise<void> {
    // 这里可以初始化一些内置服务
    // 例如：日志服务、配置服务等
  }
  
  // 应用插件
  private async applyPlugins(): Promise<void> {
    for (const plugin of Array.from(this.registry.plugins.values())) {
      try {
        plugin.install(this)
      } catch (error) {
        console.error(`Failed to apply plugin '${plugin.name}':`, error)
      }
    }
  }
  
  // 应用中间件
  private applyMiddleware(): void {
    // 中间件已在注册时按优先级排序
  }
  
  // 获取配置
  getConfig(): ServiceConfig {
    return this.registry.config
  }
  
  // 更新配置
  updateConfig(config: Partial<ServiceConfig>): void {
    this.registry.config = { ...this.registry.config, ...config }
    this.emit('configUpdated', { config: this.registry.config })
  }
  
  // 获取注册表信息
  getRegistryInfo(): string[] {
    return Array.from(this.registry.services.keys())
  }
  
  // 获取统计信息
  getMetrics(): Record<string, any> {
    return Object.fromEntries(this.metrics)
  }
  
  // 记录指标
  private recordMetric(type: string, value: any): void {
    if (this.config.enableMetrics) {
      const key = `${type}_${Date.now()}`
      this.metrics.set(key, { type, value, timestamp: Date.now() })
    }
  }
  
  // 清除注册表
  clearRegistry(): void {
    this.registry.services.clear()
    this.registry.plugins.clear()
    this.registry.middleware = []
    this.emit('registryCleared', { timestamp: Date.now() })
  }
  
  // 重置服务管理器
  reset(): void {
    this.clearRegistry()
    this.metrics.clear()
    this.initialized = false
    this.emit('reset', { timestamp: Date.now() })
  }
  
  // 销毁服务管理器
  destroy(): void {
    this.reset()
    // 移除所有事件监听器
    this.eventBus = new EventTarget()
    this.emit('destroyed', { timestamp: Date.now() })
  }
  
  // 创建默认配置
  private createDefaultConfig(): ServiceConfig {
    return {
      baseUrl: '/api',
      timeout: 10000,
      retries: 3,
      api: {
        version: 'v1',
        endpoints: {},
        headers: {
          'Content-Type': 'application/json',
        },
      },
      auth: {
        type: 'jwt',
        tokenKey: 'access_token',
        refreshKey: 'refresh_token',
        expireTime: 3600,
      },
      cache: {
        enabled: true,
        ttl: 300,
        maxSize: 100,
        strategy: 'lru',
      },
      logging: {
        level: 'info',
        enabled: true,
        maxFiles: 5,
        maxSize: '10MB',
      },
    }
  }
  
  // 调用服务方法（支持中间件）
  async callService(serviceName: string, method: string, ...args: any[]): Promise<any> {
    const service = this.getService(serviceName)
    
    if (!service || typeof service[method] !== 'function') {
      throw new Error(`Method '${method}' not found on service '${serviceName}'`)
    }
    
    // 应用中间件
    let index = 0
    const next = async (): Promise<any> => {
      if (index < this.registry.middleware.length) {
        const middleware = this.registry.middleware[index++]
        return middleware.execute({ serviceName, method, args }, next)
      } else {
        return service[method](...args)
      }
    }
    
    return next()
  }
  
  // 检查是否已初始化
  isReady(): boolean {
    return this.initialized
  }
}

// 导出服务管理器实例
export const serviceManager = ServiceManager.getInstance()

// 导出初始化函数
export const setupServices = async (config?: Partial<ServiceManagerConfig>): Promise<void> => {
  await serviceManager.initialize(config)
}

// 导出服务装饰器
export function Service(name: string) {
  return function <T extends { new (...args: any[]): {} }>(constructor: T) {
    return class extends constructor {
      constructor(...args: any[]) {
        super(...args)
        serviceManager.registerService(name, this)
      }
    }
  }
}

// 导出依赖注入装饰器
export function Inject(serviceName: string) {
  return function (target: any, propertyKey: string) {
    Object.defineProperty(target, propertyKey, {
      get: () => serviceManager.getService(serviceName),
      enumerable: true,
      configurable: true,
    })
  }
}

// 导出服务常量
export const ServiceConstants = {
  STATUS: {
    PENDING: 'pending',
    ACTIVE: 'active',
    INACTIVE: 'inactive',
    ERROR: 'error',
  },
  EVENTS: {
    INITIALIZED: 'initialized',
    SERVICE_REGISTERED: 'serviceRegistered',
    SERVICE_UNREGISTERED: 'serviceUnregistered',
    PLUGIN_REGISTERED: 'pluginRegistered',
    MIDDLEWARE_REGISTERED: 'middlewareRegistered',
    CONFIG_UPDATED: 'configUpdated',
    REGISTRY_CLEARED: 'registryCleared',
    RESET: 'reset',
    DESTROYED: 'destroyed',
  },
}

// 导出服务工具函数
export const ServiceUtils = {
  // 等待服务管理器初始化
  async waitForReady(timeout = 10000): Promise<void> {
    const startTime = Date.now()
    while (!serviceManager.isReady()) {
      if (Date.now() - startTime > timeout) {
        throw new Error('ServiceManager initialization timeout')
      }
      await new Promise(resolve => setTimeout(resolve, 100))
    }
  },

  // 批量调用服务方法
  async batchCall(calls: Array<{ service: string; method: string; args: any[] }>): Promise<any[]> {
    const promises = calls.map(call => 
      serviceManager.callService(call.service, call.method, ...call.args)
    )
    return Promise.all(promises)
  },

  // 获取服务健康状态
  getServiceHealth(): Record<string, any> {
    const services = serviceManager.getRegistryInfo()
    const health: Record<string, any> = {}
    
    services.forEach(serviceName => {
      try {
        const service = serviceManager.getService(serviceName)
        health[serviceName] = {
          status: ServiceConstants.STATUS.ACTIVE,
          available: true,
          type: typeof service,
        }
      } catch (error) {
        health[serviceName] = {
          status: ServiceConstants.STATUS.ERROR,
          available: false,
          error: (error as Error).message,
        }
      }
    })
    
    return health
  },
}

// 导出类型守卫
export const ServiceTypeGuards = {
  isServiceConfig(obj: any): obj is ServiceConfig {
    return obj && typeof obj.baseUrl === 'string' && typeof obj.timeout === 'number'
  },

  isServicePlugin(obj: any): obj is ServicePlugin {
    return obj && typeof obj.name === 'string' && typeof obj.install === 'function'
  },

  isServiceMiddleware(obj: any): obj is ServiceMiddleware {
    return obj && typeof obj.name === 'string' && typeof obj.execute === 'function'
  },
}

// 版本信息
export const VERSION = '1.0.0'

// 服务状态枚举
export enum ServiceStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error',
  DESTROYED = 'destroyed',
}

// 服务优先级枚举
export enum ServicePriority {
  HIGHEST = 1000,
  HIGH = 800,
  NORMAL = 500,
  LOW = 200,
  LOWEST = 100,
}

// 服务生命周期钩子接口
export interface ServiceLifecycleHooks {
  onInit?(): Promise<void> | void
  onStart?(): Promise<void> | void
  onStop?(): Promise<void> | void
  onDestroy?(): Promise<void> | void
}

// 服务健康检查接口
export interface ServiceHealthCheck {
  name: string
  check(): Promise<boolean>
  timeout?: number
}

// 服务监控接口
export interface ServiceMonitor {
  name: string
  metrics: Record<string, any>
  collect(): Promise<Record<string, any>>
}

// 服务配置验证器
export class ServiceConfigValidator {
  static validate(config: Partial<ServiceConfig>): boolean {
    // 基础验证逻辑
    if (config.timeout && config.timeout <= 0) {
      throw new Error('Timeout must be positive')
    }
    if (config.retries && config.retries < 0) {
      throw new Error('Retries must be non-negative')
    }
    return true
  }
}

// 服务错误类
export class ServiceError extends Error {
  constructor(
    message: string,
    public code: string,
    public service?: string
  ) {
    super(message)
    this.name = 'ServiceError'
  }
}

export class ServiceNotFoundError extends ServiceError {
  constructor(serviceName: string) {
    super(`Service '${serviceName}' not found`, 'SERVICE_NOT_FOUND', serviceName)
    this.name = 'ServiceNotFoundError'
  }
}

export class ServiceInitializationError extends ServiceError {
  constructor(serviceName: string, cause?: Error) {
    super(
      `Failed to initialize service '${serviceName}': ${cause?.message || 'Unknown error'}`,
      'SERVICE_INIT_ERROR',
      serviceName
    )
    this.name = 'ServiceInitializationError'
  }
}

// 服务事件类型
export type ServiceEventType = 
  | 'initialized'
  | 'serviceRegistered'
  | 'serviceUnregistered'
  | 'pluginRegistered'
  | 'middlewareRegistered'
  | 'configUpdated'
  | 'registryCleared'
  | 'reset'
  | 'destroyed'

// 服务事件发射器
export class ServiceEventEmitter extends EventTarget {
  emit<T = any>(type: ServiceEventType, detail?: T): void {
    this.dispatchEvent(new CustomEvent(type, { detail }))
  }

  on<T = any>(type: ServiceEventType, listener: (event: CustomEvent<T>) => void): void {
    this.addEventListener(type, listener as EventListener)
  }

  off<T = any>(type: ServiceEventType, listener: (event: CustomEvent<T>) => void): void {
    this.removeEventListener(type, listener as EventListener)
  }
}

// 默认导出服务管理器实例
export default serviceManager

// 所有类型已通过 export interface 导出，无需重复导出