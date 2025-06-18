/// <reference types="vue" />
/// <reference types="node" />
/// <reference path="../../env.d.ts" />
import type { App } from 'vue'

// 布局组件 (仅导出实际存在的组件)
// export { default as AppHeader } from './layout/AppHeader.vue'
// export { default as AppSidebar } from './layout/AppSidebar.vue'
// export { default as AppFooter } from './layout/AppFooter.vue'
// export { default as AppBreadcrumb } from './layout/AppBreadcrumb.vue'
// export { default as AppTabs } from './layout/AppTabs.vue'

// 图表组件 (仅导出实际存在的组件)
// export { default as LineChart } from './charts/LineChart.vue'
// export { default as PieChart } from './charts/PieChart.vue'

// 组件类型定义
export interface ComponentConfig {
  name: string
  component: any
  props?: Record<string, any>
  global?: boolean
  lazy?: boolean
  dependencies?: string[]
  version?: string
  description?: string
  author?: string
  tags?: string[]
  category?: string
}

// 组件注册表接口
export interface ComponentRegistry {
  components: Map<string, ComponentConfig>
  plugins: Map<string, any>
  themes: Map<string, any>
  locales: Map<string, any>
}

// 组件管理器配置
export interface ComponentManagerConfig {
  prefix?: string
  globalComponents?: string[]
  lazyLoad?: boolean
  theme?: string
  locale?: string
  development?: boolean
  autoInstall?: boolean
}

// 组件管理器类
export class ComponentManager {
  private static instance: ComponentManager
  private registry: ComponentRegistry
  private config: ComponentManagerConfig
  private app?: any
  private initialized = false
  private eventListeners = new Map<string, Function[]>()

  private constructor(config: ComponentManagerConfig = {}) {
    this.config = {
      prefix: 'E',
      globalComponents: [],
      lazyLoad: false,
      theme: 'default',
      locale: 'zh-CN',
      development: false,
      autoInstall: true,
      ...config
    }

    this.registry = {
      components: new Map(),
      plugins: new Map(),
      themes: new Map(),
      locales: new Map()
    }
  }

  // 获取单例实例
  static getInstance(config?: ComponentManagerConfig): ComponentManager {
    if (!ComponentManager.instance) {
      ComponentManager.instance = new ComponentManager(config)
    }
    return ComponentManager.instance
  }

  // 初始化组件管理器
  initialize(app: any): void {
    if (this.initialized) {
      console.warn('ComponentManager already initialized')
      return
    }

    this.app = app
    this.initialized = true

    // 注册全局组件
    this.registerGlobalComponents()

    // 安装插件
    this.installPlugins()

    // 设置主题
    this.setTheme(this.config.theme!)

    // 设置语言
    this.setLocale(this.config.locale!)

    // 触发初始化事件
    this.emit('initialized', this)

    if (this.config.development) {
      console.log('ComponentManager initialized successfully')
    }
  }

  // 注册组件
  registerComponent(config: ComponentConfig): void {
    const { name, component, global = false } = config
    
    // 添加前缀
    const componentName = this.config.prefix ? `${this.config.prefix}${name}` : name
    
    // 存储到注册表
    this.registry.components.set(componentName, config)
    
    // 全局注册
    if (global && this.app) {
      this.app.component(componentName, component)
    }
    
    // 触发注册事件
    this.emit('component:registered', { name: componentName, config })
    
    if (this.config.development) {
      console.log(`Component registered: ${componentName}`)
    }
  }

  // 批量注册组件
  registerComponents(configs: ComponentConfig[]): void {
    configs.forEach(config => this.registerComponent(config))
  }

  // 获取组件
  getComponent(name: string): ComponentConfig | undefined {
    const componentName = this.config.prefix ? `${this.config.prefix}${name}` : name
    return this.registry.components.get(componentName)
  }

  // 获取所有组件
  getAllComponents(): ComponentConfig[] {
    return Array.from(this.registry.components.values())
  }

  // 按分类获取组件
  getComponentsByCategory(category: string): ComponentConfig[] {
    return this.getAllComponents().filter(config => config.category === category)
  }

  // 按标签获取组件
  getComponentsByTag(tag: string): ComponentConfig[] {
    return this.getAllComponents().filter(config => config.tags?.includes(tag))
  }

  // 搜索组件
  searchComponents(query: string): ComponentConfig[] {
    const lowerQuery = query.toLowerCase()
    return this.getAllComponents().filter(config => 
      config.name.toLowerCase().includes(lowerQuery) ||
      config.description?.toLowerCase().includes(lowerQuery) ||
      config.tags?.some(tag => tag.toLowerCase().includes(lowerQuery))
    )
  }

  // 检查组件是否存在
  hasComponent(name: string): boolean {
    const componentName = this.config.prefix ? `${this.config.prefix}${name}` : name
    return this.registry.components.has(componentName)
  }

  // 注册插件
  registerPlugin(name: string, plugin: any): void {
    this.registry.plugins.set(name, plugin)
    
    if (this.app) {
      this.app.use(plugin)
    }
    
    this.emit('plugin:registered', { name, plugin })
    
    if (this.config.development) {
      console.log(`Plugin registered: ${name}`)
    }
  }

  // 获取插件
  getPlugin(name: string): any | undefined {
    return this.registry.plugins.get(name)
  }

  // 注册主题
  registerTheme(name: string, theme: any): void {
    this.registry.themes.set(name, theme)
    
    this.emit('theme:registered', { name, theme })
    
    if (this.config.development) {
      console.log(`Theme registered: ${name}`)
    }
  }

  // 设置主题
  setTheme(name: string): void {
    const theme = this.registry.themes.get(name)
    if (theme) {
      this.config.theme = name
      this.applyTheme(theme)
      this.emit('theme:changed', { name, theme })
    } else {
      console.warn(`Theme not found: ${name}`)
    }
  }

  // 应用主题
  private applyTheme(theme: any): void {
    // 设置 CSS 变量
    if (theme.variables) {
      const root = document.documentElement
      Object.entries(theme.variables).forEach(([key, value]) => {
        root.style.setProperty(`--${key}`, value as string)
      })
    }
    
    // 设置主题类名
    if (theme.className) {
      document.body.className = theme.className
    }
  }

  // 注册语言包
  registerLocale(name: string, locale: any): void {
    this.registry.locales.set(name, locale)
    
    this.emit('locale:registered', { name, locale })
    
    if (this.config.development) {
      console.log(`Locale registered: ${name}`)
    }
  }

  // 设置语言
  setLocale(name: string): void {
    const locale = this.registry.locales.get(name)
    if (locale) {
      this.config.locale = name
      this.applyLocale(locale)
      this.emit('locale:changed', { name, locale })
    } else {
      console.warn(`Locale not found: ${name}`)
    }
  }

  // 应用语言
  private applyLocale(locale: any): void {
    // 设置文档语言
    document.documentElement.lang = this.config.locale!
  }

  // 注册全局组件
  private registerGlobalComponents(): void {
    if (!this.config.globalComponents?.length || !this.app) return
    
    this.config.globalComponents.forEach(name => {
      const config = this.getComponent(name)
      if (config) {
        const componentName = this.config.prefix ? `${this.config.prefix}${name}` : name
        this.app!.component(componentName, config.component)
      }
    })
  }

  // 安装插件
  private installPlugins(): void {
    if (!this.app) return
    
    this.registry.plugins.forEach((plugin, name) => {
      this.app!.use(plugin)
    })
  }

  // 懒加载组件
  async loadComponent(name: string): Promise<any | null> {
    const config = this.getComponent(name)
    if (!config) {
      console.warn(`Component not found: ${name}`)
      return null
    }
    
    if (config.lazy) {
      try {
        // 动态导入组件
        const module = await import(`./components/${name}.vue`)
        return module.default
      } catch (error) {
        console.error(`Failed to load component: ${name}`, error)
        return null
      }
    }
    
    return config.component
  }

  // 获取组件依赖
  getComponentDependencies(name: string): string[] {
    const config = this.getComponent(name)
    return config?.dependencies || []
  }

  // 检查组件依赖
  checkDependencies(name: string): boolean {
    const dependencies = this.getComponentDependencies(name)
    return dependencies.every(dep => this.hasComponent(dep))
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
  getConfig(): ComponentManagerConfig {
    return { ...this.config }
  }

  // 更新配置
  updateConfig(config: Partial<ComponentManagerConfig>): void {
    this.config = { ...this.config, ...config }
    this.emit('config:updated', this.config)
  }

  // 获取注册表信息
  getRegistryInfo(): {
    components: number
    plugins: number
    themes: number
    locales: number
  } {
    return {
      components: this.registry.components.size,
      plugins: this.registry.plugins.size,
      themes: this.registry.themes.size,
      locales: this.registry.locales.size
    }
  }

  // 获取组件统计信息
  getComponentStats(): {
    total: number
    global: number
    lazy: number
    categories: Record<string, number>
    tags: Record<string, number>
  } {
    const components = this.getAllComponents()
    const stats = {
      total: components.length,
      global: components.filter(c => c.global).length,
      lazy: components.filter(c => c.lazy).length,
      categories: {} as Record<string, number>,
      tags: {} as Record<string, number>
    }

    components.forEach(component => {
      // 统计分类
      if (component.category) {
        stats.categories[component.category] = (stats.categories[component.category] || 0) + 1
      }

      // 统计标签
      if (component.tags) {
        component.tags.forEach(tag => {
          stats.tags[tag] = (stats.tags[tag] || 0) + 1
        })
      }
    })

    return stats
  }

  // 清除注册表
  clearRegistry(): void {
    this.registry.components.clear()
    this.registry.plugins.clear()
    this.registry.themes.clear()
    this.registry.locales.clear()
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
    ComponentManager.instance = null as any
  }
}

// 组件注册表（向后兼容）
const componentRegistry = new Map<string, any>()

// 组件工具函数
export const componentUtils = {
  /**
   * 注册组件
   */
  register: (name: string, component: any) => {
    componentRegistry.set(name, component)
  },
  
  /**
   * 获取组件
   */
  get: (name: string) => {
    return componentRegistry.get(name)
  },
  
  /**
   * 检查组件是否存在
   */
  has: (name: string) => {
    return componentRegistry.has(name)
  },
  
  /**
   * 获取所有组件
   */
  getAll: () => {
    return Array.from(componentRegistry.entries())
  },
  
  /**
   * 动态导入组件
   */
  dynamicImport: async (path: string) => {
    try {
      const module = await import(path)
      return module.default || module
    } catch (error) {
      console.error(`Failed to import component from ${path}:`, error)
      return null
    }
  },
  
  /**
   * 懒加载组件
   */
  lazy: (importFn: () => Promise<any>) => {
    return defineAsyncComponent({
      loader: importFn,
      loadingComponent: () => h('div', { class: 'component-loading' }, 'Loading...'),
      errorComponent: () => h('div', { class: 'component-error' }, 'Failed to load component'),
      delay: 200,
      timeout: 3000
    })
  }
}

// 组件混入
export const componentMixins = {
  /**
   * 基础混入
   */
  base: {
    props: {
      loading: {
        type: Boolean,
        default: false
      },
      disabled: {
        type: Boolean,
        default: false
      },
      size: {
        type: String,
        default: 'default',
        validator: (value: string) => ['small', 'default', 'large'].includes(value)
      }
    },
    
    computed: {
      componentClasses(this: any) {
        return {
          'is-loading': this.loading,
          'is-disabled': this.disabled,
          [`size-${this.size}`]: true
        }
      }
    }
  },
  
  /**
   * 表单混入
   */
  form: {
    props: {
      modelValue: {
        type: [String, Number, Boolean, Array, Object],
        default: undefined
      },
      placeholder: {
        type: String,
        default: ''
      },
      clearable: {
        type: Boolean,
        default: false
      },
      readonly: {
        type: Boolean,
        default: false
      }
    },
    
    emits: ['update:modelValue', 'change', 'blur', 'focus'],
    
    computed: {
      currentValue: {
        get(this: any) {
          return this.modelValue
        },
        set(this: any, value: any) {
          this.$emit('update:modelValue', value)
          this.$emit('change', value)
        }
      }
    }
  },
  
  /**
   * 权限混入
   */
  permission: {
    props: {
      permission: {
        type: [String, Array],
        default: null
      },
      role: {
        type: [String, Array],
        default: null
      }
    },
    
    computed: {
      hasPermission() {
        // 这里应该结合实际的权限系统
        return true
      }
    }
  }
}

// 组件指令
export const componentDirectives = {
  /**
   * 权限指令
   */
  permission: {
    mounted(el: HTMLElement, binding: any) {
      const { value } = binding
      // 权限检查逻辑
      if (!checkPermission(value)) {
        el.style.display = 'none'
      }
    },
    
    updated(el: HTMLElement, binding: any) {
      const { value } = binding
      if (!checkPermission(value)) {
        el.style.display = 'none'
      } else {
        el.style.display = ''
      }
    }
  },
  
  /**
   * 加载指令
   */
  loading: {
    mounted(el: HTMLElement, binding: any) {
      if (binding.value) {
        el.classList.add('is-loading')
      }
    },
    
    updated(el: HTMLElement, binding: any) {
      if (binding.value) {
        el.classList.add('is-loading')
      } else {
        el.classList.remove('is-loading')
      }
    }
  },
  
  /**
   * 防抖指令
   */
  debounce: {
    mounted(el: HTMLElement, binding: any) {
      const { value, arg } = binding
      const delay = parseInt(arg) || 300
      
      let timer: NodeJS.Timeout
      
      el.addEventListener('click', () => {
        clearTimeout(timer)
        timer = setTimeout(() => {
          value()
        }, delay)
      })
    }
  },
  
  /**
   * 节流指令
   */
  throttle: {
    mounted(el: HTMLElement, binding: any) {
      const { value, arg } = binding
      const delay = parseInt(arg) || 300
      
      let lastTime = 0
      
      el.addEventListener('click', () => {
        const now = Date.now()
        if (now - lastTime > delay) {
          value()
          lastTime = now
        }
      })
    }
  }
}

// 权限检查函数
function checkPermission(permission: string | string[]): boolean {
  // 这里应该结合实际的权限系统
  return true
}

// 组件安装器
export class ComponentInstaller {
  private app: App | null = null
  private installedComponents = new Set<string>()
  
  constructor(app?: App) {
    this.app = app || null
  }
  
  /**
   * 设置应用实例
   */
  setApp(app: App) {
    this.app = app
    return this
  }
  
  /**
   * 安装单个组件
   */
  install(name: string, component: any, global = false) {
    if (!this.app) {
      throw new Error('App instance not set')
    }
    
    if (this.installedComponents.has(name)) {
      console.warn(`Component ${name} is already installed`)
      return this
    }
    
    if (global) {
      this.app.component(name, component)
    }
    
    componentUtils.register(name, component)
    this.installedComponents.add(name)
    
    return this
  }
  
  /**
   * 批量安装组件
   */
  installAll(components: ComponentConfig[]) {
    components.forEach(({ name, component, global = false }) => {
      this.install(name, component, global)
    })
    
    return this
  }
  
  /**
   * 安装指令
   */
  installDirectives() {
    if (!this.app) {
      throw new Error('App instance not set')
    }
    
    Object.entries(componentDirectives).forEach(([name, directive]) => {
      this.app!.directive(name, directive)
    })
    
    return this
  }
  
  /**
   * 获取已安装的组件列表
   */
  getInstalled() {
    return Array.from(this.installedComponents)
  }
}

// 组件配置列表（按需注册）
export const componentConfigs: ComponentConfig[] = [
  // 布局组件（按需注册）
  { name: 'AppHeader', component: () => import('./layout/AppHeader.vue' as any) },
  { name: 'AppSidebar', component: () => import('./layout/AppSidebar.vue' as any) },
  { name: 'AppFooter', component: () => import('./layout/AppFooter.vue' as any) },
  { name: 'AppBreadcrumb', component: () => import('./layout/AppBreadcrumb.vue' as any) },
  { name: 'AppTabs', component: () => import('./layout/AppTabs.vue' as any) },
  
  // 图表组件（按需注册）
  { name: 'LineChart', component: () => import('./charts/LineChart.vue' as any) },
  { name: 'PieChart', component: () => import('./charts/PieChart.vue' as any) }
]

// 默认组件配置
const defaultComponents: ComponentConfig[] = componentConfigs

// 组件装饰器
export function Component(config: Partial<ComponentConfig>) {
  return function (target: any) {
    const componentConfig: ComponentConfig = {
      name: target.name,
      component: target,
      ...config
    }
    
    // 自动注册组件
    const manager = ComponentManager.getInstance()
    manager.registerComponent(componentConfig)
    
    return target
  }
}

// 懒加载装饰器
export function Lazy(target: any) {
  const manager = ComponentManager.getInstance()
  const config = manager.getComponent(target.name)
  
  if (config) {
    config.lazy = true
  }
  
  return target
}

// 全局组件装饰器
export function Global(target: any) {
  const manager = ComponentManager.getInstance()
  const config = manager.getComponent(target.name)
  
  if (config) {
    config.global = true
  }
  
  return target
}

// 组件分类装饰器
export function Category(category: string) {
  return function (target: any) {
    const manager = ComponentManager.getInstance()
    const config = manager.getComponent(target.name)
    
    if (config) {
      config.category = category
    }
    
    return target
  }
}

// 组件标签装饰器
export function Tags(...tags: string[]) {
  return function (target: any) {
    const manager = ComponentManager.getInstance()
    const config = manager.getComponent(target.name)
    
    if (config) {
      config.tags = tags
    }
    
    return target
  }
}

// 组件依赖装饰器
export function Dependencies(...dependencies: string[]) {
  return function (target: any) {
    const manager = ComponentManager.getInstance()
    const config = manager.getComponent(target.name)
    
    if (config) {
      config.dependencies = dependencies
    }
    
    return target
  }
}

// 组件版本装饰器
export function Version(version: string) {
  return function (target: any) {
    const manager = ComponentManager.getInstance()
    const config = manager.getComponent(target.name)
    
    if (config) {
      config.version = version
    }
    
    return target
  }
}

// 组件描述装饰器
export function Description(description: string) {
  return function (target: any) {
    const manager = ComponentManager.getInstance()
    const config = manager.getComponent(target.name)
    
    if (config) {
      config.description = description
    }
    
    return target
  }
}

// 组件作者装饰器
export function Author(author: string) {
  return function (target: any) {
    const manager = ComponentManager.getInstance()
    const config = manager.getComponent(target.name)
    
    if (config) {
      config.author = author
    }
    
    return target
  }
}

// 组件常量
export const COMPONENT_CONSTANTS = {
  // 组件类型
  TYPES: {
    BASIC: 'basic',
    LAYOUT: 'layout',
    FORM: 'form',
    DISPLAY: 'display',
    NAVIGATION: 'navigation',
    FEEDBACK: 'feedback',
    DATA_ENTRY: 'data-entry',
    DATA_DISPLAY: 'data-display',
    BUSINESS: 'business',
    HOC: 'hoc',
    FUNCTIONAL: 'functional',
    CHART: 'chart'
  },
  
  // 组件状态
  STATES: {
    LOADING: 'loading',
    LOADED: 'loaded',
    ERROR: 'error',
    EMPTY: 'empty',
    DISABLED: 'disabled',
    ACTIVE: 'active',
    INACTIVE: 'inactive'
  },
  
  // 组件尺寸
  SIZES: {
    MINI: 'mini',
    SMALL: 'small',
    MEDIUM: 'medium',
    LARGE: 'large',
    EXTRA_LARGE: 'extra-large'
  },
  
  // 组件主题
  THEMES: {
    DEFAULT: 'default',
    DARK: 'dark',
    LIGHT: 'light',
    PRIMARY: 'primary',
    SUCCESS: 'success',
    WARNING: 'warning',
    ERROR: 'error',
    INFO: 'info'
  },
  
  // 组件事件
  EVENTS: {
    CLICK: 'click',
    CHANGE: 'change',
    INPUT: 'input',
    FOCUS: 'focus',
    BLUR: 'blur',
    SUBMIT: 'submit',
    RESET: 'reset',
    LOAD: 'load',
    ERROR: 'error',
    SUCCESS: 'success'
  },
  
  // 组件位置
  POSITIONS: {
    TOP: 'top',
    BOTTOM: 'bottom',
    LEFT: 'left',
    RIGHT: 'right',
    CENTER: 'center',
    TOP_LEFT: 'top-left',
    TOP_RIGHT: 'top-right',
    BOTTOM_LEFT: 'bottom-left',
    BOTTOM_RIGHT: 'bottom-right'
  },
  
  // 组件对齐方式
  ALIGNMENTS: {
    START: 'start',
    CENTER: 'center',
    END: 'end',
    STRETCH: 'stretch',
    BASELINE: 'baseline'
  }
} as const

// 创建组件管理器实例
export const componentManager = ComponentManager.getInstance()

// 安装函数
export function setupComponents(app: any, options: { components?: ComponentConfig[], config?: ComponentManagerConfig } = {}) {
  const manager = ComponentManager.getInstance(options.config)
  
  // 初始化管理器
  manager.initialize(app)
  
  // 注册默认组件
  const components = options.components || defaultComponents
  
  // 处理异步组件
  const processedComponents = components.map(config => ({
    ...config,
    component: typeof config.component === 'function' 
      ? componentUtils.lazy(config.component as () => Promise<any>)
      : config.component
  }))
  
  // 注册组件
  manager.registerComponents(processedComponents)
  
  // 创建安装器（向后兼容）
  const installer = new ComponentInstaller(app)
  installer
    .installAll(processedComponents)
    .installDirectives()
  
  // 在开发环境下添加调试信息
  if (process.env.NODE_ENV === 'development') {
    app.config.globalProperties.$components = componentUtils
    app.config.globalProperties.$componentManager = manager
    console.log('[Components] Installed:', installer.getInstalled())
    console.log('[ComponentManager] Registry Info:', manager.getRegistryInfo())
    console.log('[ComponentManager] Component Stats:', manager.getComponentStats())
  }
  
  return { installer, manager }
}

// 导入必要的 Vue 函数
import { defineAsyncComponent, h } from 'vue'

export default {
  install: setupComponents
}