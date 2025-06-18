// 类型定义主入口文件
// 统一导出所有类型定义

// 导出实际存在的类型模块
export * from './common'
export * from './user'
export * from './knowledge'

// 重新导出常用类型
export type {
  ApiResponse,
  PaginatedResponse,
  ValidationError,
  BaseQuery,
  FileInfo,
  UploadConfig,
  UploadProgress,
  MenuItem,
  BreadcrumbItem,
  TabItem,
  Notification,
  SystemSettings,
  Statistics,
  TableColumn,
  TableConfig,
  FormField,
  FormConfig,
  ThemeConfig,
  Option,
  TreeNode
} from './common'

export type {
  User,
  UserRole,
  UserStatus,
  UserProfile,
  LoginForm,
  RegisterForm,
  LoginResponse,
  Permission,
  Role,
  Department
} from './user'

export type {
  Entity,
  Relation,
  Document,
  KnowledgeGraph,
  EntityType,
  RelationType,
  DocumentType,
  SearchQuery,
  SearchResult,
  SearchResponse,
  GraphAnalysis,
  Recommendation
} from './knowledge'

// 类型管理器配置
export interface TypeConfig {
  strict: boolean
  validation: boolean
  serialization: boolean
  documentation: boolean
}

// 类型验证器
export interface TypeValidator<T = any> {
  name: string
  validate: (value: any) => value is T
  serialize?: (value: T) => any
  deserialize?: (value: any) => T
  schema?: any
  examples?: T[]
  description?: string
}

// 类型注册表
export interface TypeRegistry {
  validators: Map<string, TypeValidator>
  schemas: Map<string, any>
  examples: Map<string, any[]>
  documentation: Map<string, string>
}

// 类型管理器
export class TypeManager {
  private static instance: TypeManager
  private registry: TypeRegistry
  private config: TypeConfig

  private constructor(config: Partial<TypeConfig> = {}) {
    this.config = {
      strict: true,
      validation: true,
      serialization: true,
      documentation: true,
      ...config
    }
    this.registry = {
      validators: new Map(),
      schemas: new Map(),
      examples: new Map(),
      documentation: new Map()
    }
    this.initializeBuiltinTypes()
  }

  static getInstance(config?: Partial<TypeConfig>): TypeManager {
    if (!TypeManager.instance) {
      TypeManager.instance = new TypeManager(config)
    }
    return TypeManager.instance
  }

  // 注册类型验证器
  registerValidator<T>(name: string, validator: TypeValidator<T>): void {
    this.registry.validators.set(name, validator)
    if (validator.schema) {
      this.registry.schemas.set(name, validator.schema)
    }
    if (validator.examples) {
      this.registry.examples.set(name, validator.examples)
    }
    if (validator.description) {
      this.registry.documentation.set(name, validator.description)
    }
  }

  // 获取类型验证器
  getValidator<T>(name: string): TypeValidator<T> | undefined {
    return this.registry.validators.get(name) as TypeValidator<T>
  }

  // 验证类型
  validate<T>(name: string, value: any): value is T {
    if (!this.config.validation) return true
    const validator = this.getValidator<T>(name)
    return validator ? validator.validate(value) : false
  }

  // 序列化
  serialize<T>(name: string, value: T): any {
    if (!this.config.serialization) return value
    const validator = this.getValidator<T>(name)
    return validator?.serialize ? validator.serialize(value) : value
  }

  // 反序列化
  deserialize<T>(name: string, value: any): T {
    if (!this.config.serialization) return value
    const validator = this.getValidator<T>(name)
    return validator?.deserialize ? validator.deserialize(value) : value
  }

  // 获取类型架构
  getSchema(name: string): any {
    return this.registry.schemas.get(name)
  }

  // 获取类型示例
  getExamples(name: string): any[] {
    return this.registry.examples.get(name) || []
  }

  // 获取类型文档
  getDocumentation(name: string): string | undefined {
    return this.registry.documentation.get(name)
  }

  // 获取所有注册的类型
  getRegisteredTypes(): string[] {
    return Array.from(this.registry.validators.keys())
  }

  // 检查类型是否注册
  isRegistered(name: string): boolean {
    return this.registry.validators.has(name)
  }

  // 初始化内置类型
  private initializeBuiltinTypes(): void {
    // 基础类型
    this.registerValidator('string', {
      name: 'string',
      validate: (value): value is string => typeof value === 'string',
      description: '字符串类型'
    })

    this.registerValidator('number', {
      name: 'number',
      validate: (value): value is number => typeof value === 'number' && !isNaN(value),
      description: '数字类型'
    })

    this.registerValidator('boolean', {
      name: 'boolean',
      validate: (value): value is boolean => typeof value === 'boolean',
      description: '布尔类型'
    })

    this.registerValidator('array', {
      name: 'array',
      validate: (value): value is any[] => Array.isArray(value),
      description: '数组类型'
    })

    this.registerValidator('object', {
      name: 'object',
      validate: (value): value is object => typeof value === 'object' && value !== null && !Array.isArray(value),
      description: '对象类型'
    })

    this.registerValidator('date', {
      name: 'date',
      validate: (value): value is Date => value instanceof Date && !isNaN(value.getTime()),
      serialize: (value: Date) => value.toISOString(),
      deserialize: (value: string) => new Date(value),
      description: '日期类型'
    })

    // 复合类型
    this.registerValidator('email', {
      name: 'email',
      validate: (value): value is string => {
        if (typeof value !== 'string') return false
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        return emailRegex.test(value)
      },
      description: '邮箱地址类型'
    })

    this.registerValidator('url', {
      name: 'url',
      validate: (value): value is string => {
        if (typeof value !== 'string') return false
        try {
          new URL(value)
          return true
        } catch {
          return false
        }
      },
      description: 'URL 地址类型'
    })

    this.registerValidator('uuid', {
      name: 'uuid',
      validate: (value): value is string => {
        if (typeof value !== 'string') return false
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
        return uuidRegex.test(value)
      },
      description: 'UUID 类型'
    })
  }
}

// 类型装饰器
export function Type<T>(name: string) {
  return function (target: any, propertyKey: string) {
    const typeManager = TypeManager.getInstance()
    
    // 添加类型元数据
    if (!target.constructor.__types__) {
      target.constructor.__types__ = new Map()
    }
    target.constructor.__types__.set(propertyKey, name)
    
    // 创建属性描述符
    let value: T
    
    const getter = function (this: any): T {
      return value
    }
    
    const setter = function (this: any, newValue: T): void {
      if (typeManager.validate<T>(name, newValue)) {
        value = newValue
      } else {
        throw new TypeError(`Invalid type for property ${propertyKey}: expected ${name}`)
      }
    }
    
    Object.defineProperty(target, propertyKey, {
      get: getter,
      set: setter,
      enumerable: true,
      configurable: true
    })
  }
}

// 类型验证装饰器
export function Validate<T>(validator: (value: T) => boolean, message?: string) {
  return function (target: any, propertyKey: string) {
    let value: T
    
    const getter = function (this: any): T {
      return value
    }
    
    const setter = function (this: any, newValue: T): void {
      if (validator(newValue)) {
        value = newValue
      } else {
        throw new TypeError(message || `Validation failed for property ${propertyKey}`)
      }
    }
    
    Object.defineProperty(target, propertyKey, {
      get: getter,
      set: setter,
      enumerable: true,
      configurable: true
    })
  }
}

// 类型转换装饰器
export function Transform<T, U>(transformer: (value: T) => U) {
  return function (target: any, propertyKey: string) {
    let value: U
    
    const getter = function (this: any): U {
      return value
    }
    
    const setter = function (this: any, newValue: T): void {
      value = transformer(newValue)
    }
    
    Object.defineProperty(target, propertyKey, {
      get: getter,
      set: setter,
      enumerable: true,
      configurable: true
    })
  }
}

// 类型工具函数
export const TypeUtils = {
  // 检查类型
  is<T>(value: any, typeName: string): value is T {
    const typeManager = TypeManager.getInstance()
    return typeManager.validate<T>(typeName, value)
  },
  
  // 断言类型
  assert<T>(value: any, typeName: string, message?: string): asserts value is T {
    if (!this.is<T>(value, typeName)) {
      throw new TypeError(message || `Expected ${typeName}, got ${typeof value}`)
    }
  },
  
  // 安全转换
  safeCast<T>(value: any, typeName: string, defaultValue: T): T {
    return this.is<T>(value, typeName) ? value : defaultValue
  },
  
  // 获取类型名称
  getTypeName(value: any): string {
    if (value === null) return 'null'
    if (value === undefined) return 'undefined'
    if (Array.isArray(value)) return 'array'
    if (value instanceof Date) return 'date'
    if (value instanceof RegExp) return 'regexp'
    return typeof value
  },
  
  // 深度克隆
  deepClone<T>(value: T): T {
    if (value === null || typeof value !== 'object') return value
    if (value instanceof Date) return new Date(value.getTime()) as T
    if (value instanceof Array) return value.map(item => this.deepClone(item)) as T
    if (typeof value === 'object') {
      const cloned = {} as T
      for (const key in value) {
        if (value.hasOwnProperty(key)) {
          cloned[key] = this.deepClone(value[key])
        }
      }
      return cloned
    }
    return value
  },
  
  // 深度比较
  deepEqual(a: any, b: any): boolean {
    if (a === b) return true
    if (a === null || b === null) return false
    if (typeof a !== typeof b) return false
    
    if (Array.isArray(a) && Array.isArray(b)) {
      if (a.length !== b.length) return false
      return a.every((item, index) => this.deepEqual(item, b[index]))
    }
    
    if (typeof a === 'object') {
      const keysA = Object.keys(a)
      const keysB = Object.keys(b)
      if (keysA.length !== keysB.length) return false
      return keysA.every(key => this.deepEqual(a[key], b[key]))
    }
    
    return false
  },
  
  // 合并对象
  deepMerge<T extends object>(target: T, ...sources: Partial<T>[]): T {
    if (!sources.length) return target
    const source = sources.shift()
    
    if (this.isObject(target) && this.isObject(source)) {
      for (const key in source) {
        if (this.isObject(source[key])) {
          if (!target[key]) Object.assign(target, { [key]: {} })
          this.deepMerge(target[key] as any, source[key] as any)
        } else {
          Object.assign(target, { [key]: source[key] })
        }
      }
    }
    
    return this.deepMerge(target, ...sources)
  },
  
  // 检查是否为对象
  isObject(item: any): item is object {
    return item && typeof item === 'object' && !Array.isArray(item)
  },
  
  // 获取对象路径值
  getPath(obj: any, path: string, defaultValue?: any): any {
    const keys = path.split('.')
    let result = obj
    
    for (const key of keys) {
      if (result === null || result === undefined) {
        return defaultValue
      }
      result = result[key]
    }
    
    return result !== undefined ? result : defaultValue
  },
  
  // 设置对象路径值
  setPath(obj: any, path: string, value: any): void {
    const keys = path.split('.')
    const lastKey = keys.pop()!
    let current = obj
    
    for (const key of keys) {
      if (!(key in current) || !this.isObject(current[key])) {
        current[key] = {}
      }
      current = current[key]
    }
    
    current[lastKey] = value
  }
}

// 导出类型管理器实例
export const typeManager = TypeManager.getInstance()

// 导出类型常量
export const TYPE_CONSTANTS = {
  VERSION: '1.0.0',
  NAME: 'TypeSystem',
  
  // 基础类型
  BASIC_TYPES: {
    STRING: 'string',
    NUMBER: 'number',
    BOOLEAN: 'boolean',
    ARRAY: 'array',
    OBJECT: 'object',
    DATE: 'date',
    NULL: 'null',
    UNDEFINED: 'undefined'
  },
  
  // 复合类型
  COMPLEX_TYPES: {
    EMAIL: 'email',
    URL: 'url',
    UUID: 'uuid',
    PHONE: 'phone',
    COLOR: 'color',
    JSON: 'json'
  },
  
  // 验证规则
  VALIDATION_RULES: {
    REQUIRED: 'required',
    MIN_LENGTH: 'minLength',
    MAX_LENGTH: 'maxLength',
    MIN_VALUE: 'minValue',
    MAX_VALUE: 'maxValue',
    PATTERN: 'pattern',
    CUSTOM: 'custom'
  },
  
  // 错误类型
  ERROR_TYPES: {
    TYPE_ERROR: 'TypeError',
    VALIDATION_ERROR: 'ValidationError',
    SERIALIZATION_ERROR: 'SerializationError',
    DESERIALIZATION_ERROR: 'DeserializationError'
  }
} as const

// 全局类型声明
declare global {
  interface Window {
    __APP_CONFIG__: {
      apiUrl: string
      wsUrl: string
      version: string
      buildTime: string
      env: string
    }
    __INITIAL_STATE__: any
  }
}

// Vue 组件 Props 类型
export interface ComponentProps {
  [key: string]: any
}

// Vue 组件 Emits 类型
export interface ComponentEmits {
  [key: string]: (...args: any[]) => void
}

// Vue 组件实例类型
export interface ComponentInstance {
  $el: HTMLElement
  $refs: Record<string, any>
  $emit: (event: string, ...args: any[]) => void
  $nextTick: (callback?: () => void) => Promise<void>
  $forceUpdate: () => void
}

// 路由元信息类型
export interface RouteMeta {
  title?: string
  icon?: string
  hidden?: boolean
  keepAlive?: boolean
  requireAuth?: boolean
  roles?: string[]
  permissions?: string[]
  badge?: string | number
  activeMenu?: string
  noCache?: boolean
  affix?: boolean
  breadcrumb?: boolean
  sidebar?: boolean
  header?: boolean
  footer?: boolean
}

// 环境变量类型
export interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_API_BASE_URL: string
  readonly VITE_APP_WS_BASE_URL: string
  readonly VITE_APP_VERSION: string
  readonly VITE_APP_BUILD_TIME: string
  readonly VITE_APP_MOCK: string
  readonly VITE_APP_DEBUG: string
  readonly VITE_APP_UPLOAD_MAX_SIZE: string
  readonly VITE_APP_CHUNK_SIZE: string
  readonly VITE_APP_SEARCH_DEBOUNCE: string
  readonly VITE_APP_CACHE_EXPIRE: string
}

export interface ImportMeta {
  readonly env: ImportMetaEnv
}