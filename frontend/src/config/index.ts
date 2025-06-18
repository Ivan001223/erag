// 配置管理主入口文件
// 统一管理应用配置

// 导入环境变量
import type { ImportMetaEnv } from '../types'

// 基础配置接口
export interface BaseConfig {
  name: string
  version: string
  description: string
  author: string
  homepage: string
  repository: string
  license: string
}

// API 配置接口
export interface ApiConfig {
  baseURL: string
  wsURL: string
  timeout: number
  retries: number
  retryDelay: number
  enableMock: boolean
  enableCache: boolean
  cacheExpiry: number
  enableLogging: boolean
  enableMetrics: boolean
}

// 认证配置接口
export interface AuthConfig {
  tokenKey: string
  refreshTokenKey: string
  userInfoKey: string
  tokenExpiry: number
  refreshTokenExpiry: number
  autoRefresh: boolean
  loginPath: string
  homePath: string
  enableSSO: boolean
  ssoProvider?: string
}

// 上传配置接口
export interface UploadConfig {
  maxSize: number
  maxFiles: number
  chunkSize: number
  allowedTypes: string[]
  allowedExtensions: string[]
  enableChunk: boolean
  enableCompress: boolean
  compressQuality: number
  enablePreview: boolean
  previewTypes: string[]
}

// 主题配置接口
export interface ThemeConfig {
  default: string
  available: string[]
  enableDark: boolean
  enableAuto: boolean
  storageKey: string
  cssVariables: Record<string, string>
}

// 国际化配置接口
export interface I18nConfig {
  default: string
  available: string[]
  fallback: string
  storageKey: string
  enableDetection: boolean
  enablePersistence: boolean
}

// 路由配置接口
export interface RouterConfig {
  mode: 'hash' | 'history'
  base: string
  enableGuard: boolean
  enableProgress: boolean
  enableKeepAlive: boolean
  enableTransition: boolean
  transitionName: string
  scrollBehavior: 'auto' | 'smooth' | 'instant'
}

// 存储配置接口
export interface StorageConfig {
  prefix: string
  enableEncryption: boolean
  encryptionKey: string
  enableCompression: boolean
  defaultExpiry: number
  enablePersistence: boolean
  persistenceKey: string
}

// 日志配置接口
export interface LogConfig {
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal'
  enableConsole: boolean
  enableRemote: boolean
  remoteURL?: string
  enableStorage: boolean
  maxEntries: number
  enableFilter: boolean
  filters: string[]
}

// 性能配置接口
export interface PerformanceConfig {
  enableMonitoring: boolean
  enableMetrics: boolean
  enableProfiling: boolean
  sampleRate: number
  enableReporting: boolean
  reportingURL?: string
  enableOptimization: boolean
  lazyLoadThreshold: number
}

// 安全配置接口
export interface SecurityConfig {
  enableCSP: boolean
  cspDirectives: Record<string, string[]>
  enableXSS: boolean
  enableCSRF: boolean
  csrfToken?: string
  enableCORS: boolean
  allowedOrigins: string[]
  enableEncryption: boolean
  encryptionAlgorithm: string
}

// 功能配置接口
export interface FeatureConfig {
  enableKnowledgeGraph: boolean
  enableDocumentUpload: boolean
  enableSearch: boolean
  enableChat: boolean
  enableAnalytics: boolean
  enableNotifications: boolean
  enableExport: boolean
  enableImport: boolean
  enableBackup: boolean
  enableSync: boolean
}

// 限制配置接口
export interface LimitConfig {
  maxDocuments: number
  maxEntities: number
  maxRelations: number
  maxFileSize: number
  maxSearchResults: number
  maxChatHistory: number
  maxNotifications: number
  requestsPerMinute: number
  requestsPerHour: number
  requestsPerDay: number
}

// 应用配置接口
export interface AppConfig {
  base: BaseConfig
  api: ApiConfig
  auth: AuthConfig
  upload: UploadConfig
  theme: ThemeConfig
  i18n: I18nConfig
  router: RouterConfig
  storage: StorageConfig
  log: LogConfig
  performance: PerformanceConfig
  security: SecurityConfig
  features: FeatureConfig
  limits: LimitConfig
  [key: string]: any
}

// 配置管理器类
export class ConfigManager {
  private static instance: ConfigManager
  private config: AppConfig
  private watchers: Map<string, ((value: any, oldValue?: any) => void)[]>
  private validators: Map<string, (value: any) => boolean>

  private constructor() {
    this.config = this.createDefaultConfig()
    this.watchers = new Map()
    this.validators = new Map()
    this.loadFromEnv()
    this.loadFromStorage()
    this.setupValidators()
  }

  static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager()
    }
    return ConfigManager.instance
  }

  // 获取配置
  get<T = any>(key: string, defaultValue?: T): T {
    const keys = key.split('.')
    let value = this.config as any
    
    for (const k of keys) {
      if (value && typeof value === 'object' && value !== null && k in value) {
        value = value[k]
      } else {
        return defaultValue as T
      }
    }
    
    return value as T
  }

  // 设置配置
  set(key: string, value: any): void {
    const keys = key.split('.')
    const lastKey = keys.pop()!
    let current = this.config as any
    
    for (const k of keys) {
      if (!(k in current) || typeof current[k] !== 'object') {
        current[k] = {}
      }
      current = current[k]
    }
    
    // 验证值
    if (this.validators.has(key)) {
      const validator = this.validators.get(key)!
      if (!validator(value)) {
        throw new Error(`Invalid value for config key: ${key}`)
      }
    }
    
    const oldValue = current[lastKey]
    current[lastKey] = value
    
    // 触发监听器
    this.notifyWatchers(key, value, oldValue)
    
    // 保存到存储
    this.saveToStorage()
  }

  // 获取所有配置
  getAll(): AppConfig {
    return JSON.parse(JSON.stringify(this.config))
  }

  // 批量设置配置
  setAll(config: Partial<AppConfig>): void {
    const oldConfig = this.getAll()
    this.config = this.mergeConfig(this.config, config)
    
    // 触发所有监听器
    this.notifyAllWatchers(this.config, oldConfig)
    
    // 保存到存储
    this.saveToStorage()
  }

  // 重置配置
  reset(): void {
    const oldConfig = this.getAll()
    this.config = this.createDefaultConfig()
    this.loadFromEnv()
    
    // 触发所有监听器
    this.notifyAllWatchers(this.config, oldConfig)
    
    // 清除存储
    this.clearStorage()
  }

  // 监听配置变化
  watch(key: string, callback: (value: any, oldValue?: any) => void): () => void {
    if (!this.watchers.has(key)) {
      this.watchers.set(key, [])
    }
    
    const callbacks = this.watchers.get(key)!
    callbacks.push(callback)
    
    // 返回取消监听函数
    return () => {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  // 添加验证器
  addValidator(key: string, validator: (value: any) => boolean): void {
    this.validators.set(key, validator)
  }

  // 移除验证器
  removeValidator(key: string): void {
    this.validators.delete(key)
  }

  // 验证配置
  validate(key?: string): boolean {
    if (key) {
      const validator = this.validators.get(key)
      if (validator) {
        const value = this.get(key)
        return validator(value)
      }
      return true
    }
    
    // 验证所有配置
    for (const [k, validator] of this.validators) {
      const value = this.get(k)
      if (!validator(value)) {
        return false
      }
    }
    
    return true
  }

  // 导出配置
  export(): string {
    return JSON.stringify(this.config, null, 2)
  }

  // 导入配置
  import(configJson: string): void {
    try {
      const config = JSON.parse(configJson)
      this.setAll(config)
    } catch (error) {
      throw new Error('Invalid config JSON')
    }
  }

  // 创建默认配置
  private createDefaultConfig(): AppConfig {
    return {
      base: {
        name: 'ERAG',
        version: '1.0.0',
        description: 'Enterprise RAG System',
        author: 'ERAG Team',
        homepage: 'https://erag.example.com',
        repository: 'https://github.com/erag/erag',
        license: 'MIT'
      },
      api: {
        baseURL: '/api',
        wsURL: '/ws',
        timeout: 30000,
        retries: 3,
        retryDelay: 1000,
        enableMock: false,
        enableCache: true,
        cacheExpiry: 300000,
        enableLogging: true,
        enableMetrics: true
      },
      auth: {
        tokenKey: 'access_token',
        refreshTokenKey: 'refresh_token',
        userInfoKey: 'user_info',
        tokenExpiry: 3600000,
        refreshTokenExpiry: 604800000,
        autoRefresh: true,
        loginPath: '/login',
        homePath: '/dashboard',
        enableSSO: false
      },
      upload: {
        maxSize: 100 * 1024 * 1024, // 100MB
        maxFiles: 10,
        chunkSize: 2 * 1024 * 1024, // 2MB
        allowedTypes: ['application/pdf', 'text/plain', 'application/msword'],
        allowedExtensions: ['.pdf', '.txt', '.doc', '.docx'],
        enableChunk: true,
        enableCompress: true,
        compressQuality: 0.8,
        enablePreview: true,
        previewTypes: ['image/*', 'text/*']
      },
      theme: {
        default: 'light',
        available: ['light', 'dark', 'auto'],
        enableDark: true,
        enableAuto: true,
        storageKey: 'app_theme',
        cssVariables: {}
      },
      i18n: {
        default: 'zh-CN',
        available: ['zh-CN', 'en-US'],
        fallback: 'en-US',
        storageKey: 'app_locale',
        enableDetection: true,
        enablePersistence: true
      },
      router: {
        mode: 'history',
        base: '/',
        enableGuard: true,
        enableProgress: true,
        enableKeepAlive: true,
        enableTransition: true,
        transitionName: 'fade',
        scrollBehavior: 'smooth'
      },
      storage: {
        prefix: 'erag_',
        enableEncryption: false,
        encryptionKey: '',
        enableCompression: true,
        defaultExpiry: 86400000, // 24小时
        enablePersistence: true,
        persistenceKey: 'app_state'
      },
      log: {
        level: 'info',
        enableConsole: true,
        enableRemote: false,
        enableStorage: true,
        maxEntries: 1000,
        enableFilter: true,
        filters: ['debug']
      },
      performance: {
        enableMonitoring: true,
        enableMetrics: true,
        enableProfiling: false,
        sampleRate: 0.1,
        enableReporting: false,
        enableOptimization: true,
        lazyLoadThreshold: 100
      },
      security: {
        enableCSP: true,
        cspDirectives: {
          'default-src': ["'self'"],
          'script-src': ["'self'", "'unsafe-inline'"],
          'style-src': ["'self'", "'unsafe-inline'"]
        },
        enableXSS: true,
        enableCSRF: true,
        enableCORS: true,
        allowedOrigins: ['http://localhost:3000'],
        enableEncryption: false,
        encryptionAlgorithm: 'AES-256-GCM'
      },
      features: {
        enableKnowledgeGraph: true,
        enableDocumentUpload: true,
        enableSearch: true,
        enableChat: true,
        enableAnalytics: true,
        enableNotifications: true,
        enableExport: true,
        enableImport: true,
        enableBackup: false,
        enableSync: false
      },
      limits: {
        maxDocuments: 10000,
        maxEntities: 50000,
        maxRelations: 100000,
        maxFileSize: 100 * 1024 * 1024,
        maxSearchResults: 100,
        maxChatHistory: 1000,
        maxNotifications: 100,
        requestsPerMinute: 60,
        requestsPerHour: 1000,
        requestsPerDay: 10000
      }
    }
  }

  // 从环境变量加载配置
  private loadFromEnv(): void {
    const env = import.meta.env as unknown as ImportMetaEnv
    
    // API 配置
    if (env.VITE_APP_API_BASE_URL) {
      this.config.api.baseURL = env.VITE_APP_API_BASE_URL
    }
    if (env.VITE_APP_WS_BASE_URL) {
      this.config.api.wsURL = env.VITE_APP_WS_BASE_URL
    }
    
    // 基础配置
    if (env.VITE_APP_TITLE) {
      this.config.base.name = env.VITE_APP_TITLE
    }
    if (env.VITE_APP_VERSION) {
      this.config.base.version = env.VITE_APP_VERSION
    }
    
    // 上传配置
    if (env.VITE_APP_UPLOAD_MAX_SIZE) {
      this.config.upload.maxSize = parseInt(env.VITE_APP_UPLOAD_MAX_SIZE)
    }
    if (env.VITE_APP_CHUNK_SIZE) {
      this.config.upload.chunkSize = parseInt(env.VITE_APP_CHUNK_SIZE)
    }
    
    // 其他配置
    if (env.VITE_APP_MOCK === 'true') {
      this.config.api.enableMock = true
    }
    if (env.VITE_APP_DEBUG === 'true') {
      this.config.log.level = 'debug'
    }
  }

  // 从存储加载配置
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(`${this.config.storage.prefix}config`)
      if (stored) {
        const config = JSON.parse(stored)
        this.config = this.mergeConfig(this.config, config)
      }
    } catch (error) {
      console.warn('Failed to load config from storage:', error)
    }
  }

  // 保存配置到存储
  private saveToStorage(): void {
    try {
      const configToSave = {
        theme: this.config.theme,
        i18n: this.config.i18n,
        // 只保存用户可配置的部分
      }
      localStorage.setItem(`${this.config.storage.prefix}config`, JSON.stringify(configToSave))
    } catch (error) {
      console.warn('Failed to save config to storage:', error)
    }
  }

  // 清除存储
  private clearStorage(): void {
    try {
      localStorage.removeItem(`${this.config.storage.prefix}config`)
    } catch (error) {
      console.warn('Failed to clear config from storage:', error)
    }
  }

  // 合并配置
  private mergeConfig(target: any, source: any): any {
    const result = { ...target }
    
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.mergeConfig(target[key] || {}, source[key])
      } else {
        result[key] = source[key]
      }
    }
    
    return result
  }

  // 通知监听器
  private notifyWatchers(key: string, value: any, oldValue?: any): void {
    const callbacks = this.watchers.get(key)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(value, oldValue)
        } catch (error) {
          console.error('Error in config watcher:', error)
        }
      })
    }
  }

  // 通知所有监听器
  private notifyAllWatchers(newConfig: any, oldConfig: any): void {
    for (const key of this.watchers.keys()) {
      const newValue = this.get(key)
      const oldValue = this.getValueFromConfig(oldConfig, key)
      if (newValue !== oldValue) {
        this.notifyWatchers(key, newValue, oldValue)
      }
    }
  }

  // 从配置对象获取值
  private getValueFromConfig(config: any, key: string): any {
    const keys = key.split('.')
    let value = config
    
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k]
      } else {
        return undefined
      }
    }
    
    return value
  }

  // 设置验证器
  private setupValidators(): void {
    // API 配置验证
    this.addValidator('api.timeout', (value) => typeof value === 'number' && value > 0)
    this.addValidator('api.retries', (value) => typeof value === 'number' && value >= 0)
    
    // 上传配置验证
    this.addValidator('upload.maxSize', (value) => typeof value === 'number' && value > 0)
    this.addValidator('upload.chunkSize', (value) => typeof value === 'number' && value > 0)
    
    // 主题配置验证
    this.addValidator('theme.default', (value) => typeof value === 'string' && value.length > 0)
    
    // 国际化配置验证
    this.addValidator('i18n.default', (value) => typeof value === 'string' && value.length > 0)
  }
}

// 配置工具函数
export const ConfigUtils = {
  // 获取环境变量
  getEnv(key: string, defaultValue?: string): string {
    const env = import.meta.env as any
    return env[key] || defaultValue || ''
  },
  
  // 检查是否为开发环境
  isDev(): boolean {
    return import.meta.env.DEV
  },
  
  // 检查是否为生产环境
  isProd(): boolean {
    return import.meta.env.PROD
  },
  
  // 检查是否为测试环境
  isTest(): boolean {
    return import.meta.env.MODE === 'test'
  },
  
  // 获取构建时间
  getBuildTime(): string {
    return this.getEnv('VITE_APP_BUILD_TIME', new Date().toISOString())
  },
  
  // 获取版本号
  getVersion(): string {
    return this.getEnv('VITE_APP_VERSION', '1.0.0')
  },
  
  // 格式化配置值
  formatValue(value: any, type: 'string' | 'number' | 'boolean' | 'array' | 'object'): any {
    switch (type) {
      case 'string':
        return String(value)
      case 'number':
        return Number(value)
      case 'boolean':
        return Boolean(value)
      case 'array':
        return Array.isArray(value) ? value : []
      case 'object':
        return typeof value === 'object' && value !== null ? value : {}
      default:
        return value
    }
  },
  
  // 验证配置值
  validateValue(value: any, rules: any): boolean {
    if (rules.required && (value === undefined || value === null)) {
      return false
    }
    
    if (rules.type && typeof value !== rules.type) {
      return false
    }
    
    if (rules.min !== undefined && value < rules.min) {
      return false
    }
    
    if (rules.max !== undefined && value > rules.max) {
      return false
    }
    
    if (rules.pattern && !rules.pattern.test(value)) {
      return false
    }
    
    if (rules.enum && !rules.enum.includes(value)) {
      return false
    }
    
    return true
  }
}

// 导出配置管理器实例
export const configManager = ConfigManager.getInstance()

// 导出配置常量
export const CONFIG_CONSTANTS = {
  VERSION: '1.0.0',
  NAME: 'ConfigManager',
  
  // 存储键名
  STORAGE_KEYS: {
    CONFIG: 'config',
    THEME: 'theme',
    LOCALE: 'locale',
    USER_PREFERENCES: 'user_preferences'
  },
  
  // 默认值
  DEFAULTS: {
    TIMEOUT: 30000,
    RETRIES: 3,
    CHUNK_SIZE: 2 * 1024 * 1024,
    MAX_FILE_SIZE: 100 * 1024 * 1024,
    CACHE_EXPIRY: 300000
  },
  
  // 环境变量前缀
  ENV_PREFIX: 'VITE_APP_',
  
  // 配置分类
  CATEGORIES: {
    BASE: 'base',
    API: 'api',
    AUTH: 'auth',
    UPLOAD: 'upload',
    THEME: 'theme',
    I18N: 'i18n',
    ROUTER: 'router',
    STORAGE: 'storage',
    LOG: 'log',
    PERFORMANCE: 'performance',
    SECURITY: 'security',
    FEATURES: 'features',
    LIMITS: 'limits'
  }
} as const

// 类型已通过 interface 声明自动导出，无需重复导出

// 导出默认配置
export default configManager