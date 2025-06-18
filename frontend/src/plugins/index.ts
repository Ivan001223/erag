// 插件系统主入口文件
// 统一管理应用插件

// 导出所有插件模块
// 注释掉不存在的模块导出
// export * from './router'
// export * from './store'
// export * from './i18n'
// export * from './theme'
// export * from './auth'
// export * from './api'
// 注释掉不存在的模块导出
// export * from './components'
// export * from './directives'
// export * from './filters'
// export * from './mixins'
// export * from './utils'
// export * from './validation'
// 注释掉不存在的模块导出
// export * from './notification'
// export * from './loading'
// export * from './error'
// export * from './logger'
// 注释掉不存在的模块导出
// export * from './analytics'
// export * from './performance'
// export * from './security'
// export * from './accessibility'
// export * from './seo'
// export * from './pwa'
// export * from './testing'

// Vue 相关类型
import type { App, Plugin } from 'vue'

// 插件配置接口
export interface PluginConfig {
  name: string
  plugin: Plugin | (() => Plugin | Promise<Plugin>)
  options?: Record<string, any>
  dependencies?: string[]
  version?: string
  description?: string
  author?: string
  enabled?: boolean
  priority?: number
  environment?: string[]
  tags?: string[]
}

// 插件注册表接口
export interface PluginRegistry {
  plugins: Map<string, PluginConfig>
  installed: Set<string>
  dependencies: Map<string, string[]>
  hooks: Map<string, Function[]>
}

// 插件管理器配置
export interface PluginManagerConfig {
  autoInstall?: boolean
  development?: boolean
  environment?: string
  enableHooks?: boolean
  enableDependencyCheck?: boolean
  enablePrioritySort?: boolean
}

// 插件钩子类型
export type PluginHook = 'beforeInstall' | 'afterInstall' | 'beforeUninstall' | 'afterUninstall' | 'error'

// 插件管理器类
export class PluginManager {
  private static instance: PluginManager
  private registry: PluginRegistry
  private config: PluginManagerConfig
  private app?: App
  private initialized = false
  private eventListeners = new Map<string, Function[]>()

  private constructor(config: PluginManagerConfig = {}) {
    this.config = {
      autoInstall: true,
      development: false,
      environment: 'production',
      enableHooks: true,
      enableDependencyCheck: true,
      enablePrioritySort: true,
      ...config
    }

    this.registry = {
      plugins: new Map(),
      installed: new Set(),
      dependencies: new Map(),
      hooks: new Map()
    }
  }

  // 获取单例实例
  static getInstance(config?: PluginManagerConfig): PluginManager {
    if (!PluginManager.instance) {
      PluginManager.instance = new PluginManager(config)
    }
    return PluginManager.instance
  }

  // 初始化插件管理器
  initialize(app: App): void {
    if (this.initialized) {
      console.warn('PluginManager already initialized')
      return
    }

    this.app = app
    this.initialized = true

    // 自动安装插件
    if (this.config.autoInstall) {
      this.installAllPlugins()
    }

    // 触发初始化事件
    this.emit('initialized', this)

    if (this.config.development) {
      console.log('PluginManager initialized successfully')
    }
  }

  // 注册插件
  registerPlugin(config: PluginConfig): void {
    const { name, plugin, enabled = true, environment = [] } = config

    // 检查环境
    if (environment.length > 0 && !environment.includes(this.config.environment!)) {
      if (this.config.development) {
        console.log(`Plugin ${name} skipped due to environment mismatch`)
      }
      return
    }

    // 存储到注册表
    this.registry.plugins.set(name, config)

    // 存储依赖关系
    if (config.dependencies) {
      this.registry.dependencies.set(name, config.dependencies)
    }

    // 触发注册事件
    this.emit('plugin:registered', { name, config })

    if (this.config.development) {
      console.log(`Plugin registered: ${name}`)
    }

    // 自动安装（如果启用且应用已初始化）
    if (this.config.autoInstall && enabled && this.app) {
      this.installPlugin(name)
    }
  }

  // 批量注册插件
  registerPlugins(configs: PluginConfig[]): void {
    configs.forEach(config => this.registerPlugin(config))
  }

  // 安装插件
  installPlugin(name: string): boolean {
    const config = this.registry.plugins.get(name)
    if (!config) {
      console.error(`Plugin not found: ${name}`)
      return false
    }

    if (this.registry.installed.has(name)) {
      if (this.config.development) {
        console.warn(`Plugin already installed: ${name}`)
      }
      return true
    }

    if (!config.enabled) {
      if (this.config.development) {
        console.log(`Plugin disabled: ${name}`)
      }
      return false
    }

    if (!this.app) {
      console.error('App instance not available')
      return false
    }

    try {
      // 检查依赖
      if (this.config.enableDependencyCheck && !this.checkDependencies(name)) {
        console.error(`Dependencies not met for plugin: ${name}`)
        return false
      }

      // 执行安装前钩子
      if (this.config.enableHooks) {
        this.executeHook('beforeInstall', { name, config })
      }

      // 安装插件
      this.app.use(config.plugin, config.options || {})
      this.registry.installed.add(name)

      // 执行安装后钩子
      if (this.config.enableHooks) {
        this.executeHook('afterInstall', { name, config })
      }

      // 触发安装事件
      this.emit('plugin:installed', { name, config })

      if (this.config.development) {
        console.log(`Plugin installed: ${name}`)
      }

      return true
    } catch (error) {
      console.error(`Failed to install plugin ${name}:`, error)
      
      // 执行错误钩子
      if (this.config.enableHooks) {
        this.executeHook('error', { name, config, error })
      }

      // 触发错误事件
      this.emit('plugin:error', { name, config, error })

      return false
    }
  }

  // 卸载插件
  uninstallPlugin(name: string): boolean {
    const config = this.registry.plugins.get(name)
    if (!config) {
      console.error(`Plugin not found: ${name}`)
      return false
    }

    if (!this.registry.installed.has(name)) {
      if (this.config.development) {
        console.warn(`Plugin not installed: ${name}`)
      }
      return true
    }

    try {
      // 执行卸载前钩子
      if (this.config.enableHooks) {
        this.executeHook('beforeUninstall', { name, config })
      }

      // 卸载插件（Vue 3 没有直接的卸载方法，这里只是标记）
      this.registry.installed.delete(name)

      // 执行卸载后钩子
      if (this.config.enableHooks) {
        this.executeHook('afterUninstall', { name, config })
      }

      // 触发卸载事件
      this.emit('plugin:uninstalled', { name, config })

      if (this.config.development) {
        console.log(`Plugin uninstalled: ${name}`)
      }

      return true
    } catch (error) {
      console.error(`Failed to uninstall plugin ${name}:`, error)
      
      // 执行错误钩子
      if (this.config.enableHooks) {
        this.executeHook('error', { name, config, error })
      }

      // 触发错误事件
      this.emit('plugin:error', { name, config, error })

      return false
    }
  }

  // 安装所有插件
  installAllPlugins(): void {
    const plugins = Array.from(this.registry.plugins.entries())
    
    // 按优先级排序
    if (this.config.enablePrioritySort) {
      plugins.sort(([, a], [, b]) => (b.priority || 0) - (a.priority || 0))
    }

    plugins.forEach(([name]) => {
      this.installPlugin(name)
    })
  }

  // 检查插件依赖
  checkDependencies(name: string): boolean {
    const dependencies = this.registry.dependencies.get(name)
    if (!dependencies) return true

    return dependencies.every(dep => this.registry.installed.has(dep))
  }

  // 获取插件
  getPlugin(name: string): PluginConfig | undefined {
    return this.registry.plugins.get(name)
  }

  // 获取所有插件
  getAllPlugins(): PluginConfig[] {
    return Array.from(this.registry.plugins.values())
  }

  // 获取已安装插件
  getInstalledPlugins(): PluginConfig[] {
    return Array.from(this.registry.installed)
      .map(name => this.registry.plugins.get(name)!)
      .filter(Boolean)
  }

  // 获取未安装插件
  getUninstalledPlugins(): PluginConfig[] {
    return this.getAllPlugins().filter(config => !this.registry.installed.has(config.name))
  }

  // 按标签获取插件
  getPluginsByTag(tag: string): PluginConfig[] {
    return this.getAllPlugins().filter(config => config.tags?.includes(tag))
  }

  // 搜索插件
  searchPlugins(query: string): PluginConfig[] {
    const lowerQuery = query.toLowerCase()
    return this.getAllPlugins().filter(config => 
      config.name.toLowerCase().includes(lowerQuery) ||
      config.description?.toLowerCase().includes(lowerQuery) ||
      config.tags?.some(tag => tag.toLowerCase().includes(lowerQuery))
    )
  }

  // 检查插件是否已安装
  isInstalled(name: string): boolean {
    return this.registry.installed.has(name)
  }

  // 启用插件
  enablePlugin(name: string): void {
    const config = this.registry.plugins.get(name)
    if (config) {
      config.enabled = true
      this.emit('plugin:enabled', { name, config })
      
      if (this.config.development) {
        console.log(`Plugin enabled: ${name}`)
      }
    }
  }

  // 禁用插件
  disablePlugin(name: string): void {
    const config = this.registry.plugins.get(name)
    if (config) {
      config.enabled = false
      this.emit('plugin:disabled', { name, config })
      
      if (this.config.development) {
        console.log(`Plugin disabled: ${name}`)
      }
    }
  }

  // 注册钩子
  registerHook(hook: PluginHook, callback: Function): void {
    if (!this.registry.hooks.has(hook)) {
      this.registry.hooks.set(hook, [])
    }
    this.registry.hooks.get(hook)!.push(callback)
  }

  // 执行钩子
  private executeHook(hook: PluginHook, data: any): void {
    const callbacks = this.registry.hooks.get(hook)
    if (!callbacks) return

    callbacks.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error(`Error in ${hook} hook:`, error)
      }
    })
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
  getConfig(): PluginManagerConfig {
    return { ...this.config }
  }

  // 更新配置
  updateConfig(config: Partial<PluginManagerConfig>): void {
    this.config = { ...this.config, ...config }
    this.emit('config:updated', this.config)
  }

  // 获取注册表信息
  getRegistryInfo(): {
    total: number
    installed: number
    enabled: number
    disabled: number
  } {
    const plugins = this.getAllPlugins()
    return {
      total: plugins.length,
      installed: this.registry.installed.size,
      enabled: plugins.filter(p => p.enabled !== false).length,
      disabled: plugins.filter(p => p.enabled === false).length
    }
  }

  // 获取插件统计信息
  getPluginStats(): {
    byTag: Record<string, number>
    byAuthor: Record<string, number>
    byVersion: Record<string, number>
    byEnvironment: Record<string, number>
  } {
    const plugins = this.getAllPlugins()
    const stats = {
      byTag: {} as Record<string, number>,
      byAuthor: {} as Record<string, number>,
      byVersion: {} as Record<string, number>,
      byEnvironment: {} as Record<string, number>
    }

    plugins.forEach(plugin => {
      // 统计标签
      if (plugin.tags) {
        plugin.tags.forEach(tag => {
          stats.byTag[tag] = (stats.byTag[tag] || 0) + 1
        })
      }

      // 统计作者
      if (plugin.author) {
        stats.byAuthor[plugin.author] = (stats.byAuthor[plugin.author] || 0) + 1
      }

      // 统计版本
      if (plugin.version) {
        stats.byVersion[plugin.version] = (stats.byVersion[plugin.version] || 0) + 1
      }

      // 统计环境
      if (plugin.environment) {
        plugin.environment.forEach(env => {
          stats.byEnvironment[env] = (stats.byEnvironment[env] || 0) + 1
        })
      }
    })

    return stats
  }

  // 导出插件配置
  exportConfig(): PluginConfig[] {
    return this.getAllPlugins().map(config => ({
      name: config.name,
      enabled: config.enabled,
      options: config.options,
      priority: config.priority
    })) as PluginConfig[]
  }

  // 导入插件配置
  importConfig(configs: Partial<PluginConfig>[]): void {
    configs.forEach(config => {
      if (config.name) {
        const existingConfig = this.registry.plugins.get(config.name)
        if (existingConfig) {
          Object.assign(existingConfig, config)
          this.emit('plugin:config:imported', { name: config.name, config })
        }
      }
    })
  }

  // 清除注册表
  clearRegistry(): void {
    this.registry.plugins.clear()
    this.registry.installed.clear()
    this.registry.dependencies.clear()
    this.registry.hooks.clear()
    this.emit('registry:cleared')
  }

  // 重置管理器
  reset(): void {
    this.clearRegistry()
    this.eventListeners.clear()
    this.initialized = false
    this.app = undefined
    this.emit('reset')
  }

  // 销毁管理器
  destroy(): void {
    this.reset()
    PluginManager.instance = null as any
  }
}

// 插件装饰器
export function Plugin(config: Partial<PluginConfig>) {
  return function (target: any) {
    const pluginConfig: PluginConfig = {
      name: target.name || 'UnnamedPlugin',
      plugin: target,
      ...config
    }
    
    // 自动注册插件
    const manager = PluginManager.getInstance()
    manager.registerPlugin(pluginConfig)
    
    return target
  }
}

// 插件依赖装饰器
export function PluginDependencies(...dependencies: string[]) {
  return function (target: any) {
    const manager = PluginManager.getInstance()
    const config = manager.getPlugin(target.name)
    
    if (config) {
      config.dependencies = dependencies
    }
    
    return target
  }
}

// 插件优先级装饰器
export function Priority(priority: number) {
  return function (target: any) {
    const manager = PluginManager.getInstance()
    const config = manager.getPlugin(target.name)
    
    if (config) {
      config.priority = priority
    }
    
    return target
  }
}

// 插件环境装饰器
export function Environment(...environments: string[]) {
  return function (target: any) {
    const manager = PluginManager.getInstance()
    const config = manager.getPlugin(target.name)
    
    if (config) {
      config.environment = environments
    }
    
    return target
  }
}

// 插件标签装饰器
export function PluginTags(...tags: string[]) {
  return function (target: any) {
    const manager = PluginManager.getInstance()
    const config = manager.getPlugin(target.name)
    
    if (config) {
      config.tags = tags
    }
    
    return target
  }
}

// 插件工具函数
export const PluginUtils = {
  // 创建插件
  createPlugin(name: string, install: (app: App, options?: any) => void): Plugin {
    return {
      install
    }
  },
  
  // 检查插件是否为有效插件
  isValidPlugin(plugin: any): plugin is Plugin {
    return plugin && typeof plugin.install === 'function'
  },
  
  // 合并插件选项
  mergeOptions(defaultOptions: Record<string, any>, userOptions: Record<string, any>): Record<string, any> {
    return { ...defaultOptions, ...userOptions }
  },
  
  // 验证插件配置
  validateConfig(config: PluginConfig): boolean {
    if (!config.name || typeof config.name !== 'string') {
      console.error('Plugin name is required and must be a string')
      return false
    }
    
    if (!config.plugin || !this.isValidPlugin(config.plugin)) {
      console.error('Plugin must be a valid Vue plugin')
      return false
    }
    
    return true
  },
  
  // 获取插件信息
  getPluginInfo(plugin: Plugin): any {
    return {
      name: (plugin as any).name || 'Unknown',
      version: (plugin as any).version || '0.0.0',
      description: (plugin as any).description || '',
      author: (plugin as any).author || 'Unknown'
    }
  }
}

// 插件常量
export const PLUGIN_CONSTANTS = {
  // 插件类型
  TYPES: {
    CORE: 'core',
    UI: 'ui',
    UTILITY: 'utility',
    INTEGRATION: 'integration',
    DEVELOPMENT: 'development',
    PRODUCTION: 'production'
  },
  
  // 插件状态
  STATES: {
    REGISTERED: 'registered',
    INSTALLED: 'installed',
    ENABLED: 'enabled',
    DISABLED: 'disabled',
    ERROR: 'error'
  },
  
  // 插件优先级
  PRIORITIES: {
    HIGHEST: 1000,
    HIGH: 800,
    NORMAL: 500,
    LOW: 200,
    LOWEST: 0
  },
  
  // 插件环境
  ENVIRONMENTS: {
    DEVELOPMENT: 'development',
    PRODUCTION: 'production',
    TEST: 'test',
    STAGING: 'staging'
  },
  
  // 插件事件
  EVENTS: {
    REGISTERED: 'plugin:registered',
    INSTALLED: 'plugin:installed',
    UNINSTALLED: 'plugin:uninstalled',
    ENABLED: 'plugin:enabled',
    DISABLED: 'plugin:disabled',
    ERROR: 'plugin:error'
  }
} as const

// 创建插件管理器实例
export const pluginManager = PluginManager.getInstance()

// 默认插件配置
const defaultPlugins: PluginConfig[] = [
  // 暂时没有可用的插件模块
  // 注释掉不存在的 router 插件
  // {
  //   name: 'router',
  //   plugin: () => import('./router'),
  //   priority: PLUGIN_CONSTANTS.PRIORITIES.HIGHEST,
  //   tags: ['core', 'routing'],
  //   description: 'Vue Router plugin for routing'
  // }
  // 注释掉不存在的插件模块
  // {
  //   name: 'store',
  //   plugin: () => import('./store'),
  //   priority: PLUGIN_CONSTANTS.PRIORITIES.HIGHEST,
  //   tags: ['core', 'state'],
  //   description: 'Pinia store plugin for state management'
  // },
  // {
  //   name: 'i18n',
  //   plugin: () => import('./i18n'),
  //   priority: PLUGIN_CONSTANTS.PRIORITIES.HIGH,
  //   tags: ['core', 'i18n'],
  //   description: 'Vue I18n plugin for internationalization'
  // },
  // {
  //   name: 'components',
  //   plugin: () => import('./components'),
  //   priority: PLUGIN_CONSTANTS.PRIORITIES.HIGH,
  //   tags: ['ui', 'components'],
  //   description: 'Component library plugin'
  // },
  // {
  //   name: 'directives',
  //   plugin: () => import('./directives'),
  //   priority: PLUGIN_CONSTANTS.PRIORITIES.NORMAL,
  //   tags: ['ui', 'directives'],
  //   description: 'Custom directives plugin'
  // }
]

// 安装插件函数
export function setupPlugins(app: App, options: { plugins?: PluginConfig[], config?: PluginManagerConfig } = {}) {
  const manager = PluginManager.getInstance(options.config)
  
  // 初始化管理器
  manager.initialize(app)
  
  // 注册默认插件
  const plugins = options.plugins || defaultPlugins
  
  // 处理异步插件
  const processedPlugins = plugins
    .filter(config => config.plugin) // 先过滤掉没有plugin的配置
    .map(config => ({
      ...config,
      plugin: typeof config.plugin === 'function' 
        ? config.plugin(app)
        : config.plugin
    }))
  
  // 注册插件
  manager.registerPlugins(processedPlugins)
  
  // 在开发环境下添加调试信息
  if (import.meta.env.DEV) {
    app.config.globalProperties.$pluginManager = manager
    console.log('[PluginManager] Registry Info:', manager.getRegistryInfo())
    console.log('[PluginManager] Plugin Stats:', manager.getPluginStats())
  }
  
  return manager
}

// 导出默认插件管理器
export default {
  install: setupPlugins,
  manager: pluginManager
}