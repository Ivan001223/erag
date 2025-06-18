import { createPinia } from 'pinia'
import type { App } from 'vue'
import { createPersistedState } from 'pinia-plugin-persistedstate'

// 导入所有 store
export { useAppStore } from './app'
export { useUserStore } from './user'
export { useTabsStore } from './tabs'
export { useKnowledgeStore } from './knowledge'

// 其他可能存在的 store 导入
// export { useSettingsStore } from './settings'
// export { usePermissionStore } from './permission'
// export { useCacheStore } from './cache'

// 创建 pinia 实例
const pinia = createPinia()

// 配置持久化插件
pinia.use(
  createPersistedState({
    // 默认存储到 localStorage
    storage: localStorage,
    // 序列化函数
    serializer: {
      serialize: JSON.stringify,
      deserialize: JSON.parse
    },
    // 默认不持久化，需要在各个 store 中单独配置
    auto: false,
    // 调试模式
    debug: import.meta.env.DEV
  })
)

// Store 配置接口
export interface StoreConfig {
  // 是否启用持久化
  persist?: boolean
  // 持久化存储类型
  storage?: 'localStorage' | 'sessionStorage'
  // 持久化的键名
  key?: string
  // 需要持久化的路径
  paths?: string[]
  // 不需要持久化的路径
  omit?: string[]
}

// Store 状态接口
export interface StoreState {
  // 加载状态
  loading: boolean
  // 错误信息
  error: string | null
  // 最后更新时间
  lastUpdated: number
}

// Store 工具函数
export const storeUtils = {
  /**
   * 创建基础状态
   */
  createBaseState: (): StoreState => ({
    loading: false,
    error: null,
    lastUpdated: Date.now()
  }),
  
  /**
   * 设置加载状态
   */
  setLoading: (state: StoreState, loading: boolean) => {
    state.loading = loading
    if (!loading) {
      state.lastUpdated = Date.now()
    }
  },
  
  /**
   * 设置错误信息
   */
  setError: (state: StoreState, error: string | null) => {
    state.error = error
    state.loading = false
    state.lastUpdated = Date.now()
  },
  
  /**
   * 清除错误
   */
  clearError: (state: StoreState) => {
    state.error = null
  },
  
  /**
   * 重置状态
   */
  resetState: (state: StoreState) => {
    state.loading = false
    state.error = null
    state.lastUpdated = Date.now()
  }
}

// Store 装饰器
export const storeDecorators = {
  /**
   * 异步操作装饰器
   */
  withLoading: <S extends StoreState, T extends any[], R>(
    store: S,
    fn: (...args: T) => Promise<R>
  ) => {
    return async function(...args: T): Promise<R> {
      try {
        storeUtils.setLoading(store, true)
        storeUtils.clearError(store)
        const result = await fn.apply(store, args)
        storeUtils.setLoading(store, false)
        return result
      } catch (error) {
        const message = error instanceof Error ? error.message : '操作失败'
        storeUtils.setError(store, message)
        throw error
      }
    }
  },
  
  /**
   * 缓存装饰器
   */
  withCache: <S extends StoreState, T extends any[], R>(
    store: S, 
    fn: (...args: T) => Promise<R>,
    cacheKey: string,
    ttl: number = 5 * 60 * 1000 // 5分钟
  ) => {
    const cache = new Map<string, { data: R; timestamp: number }>()
    
    return async function(...args: T): Promise<R> {
      const key = `${cacheKey}_${JSON.stringify(args)}`
      const cached = cache.get(key)
      
      if (cached && Date.now() - cached.timestamp < ttl) {
        return cached.data
      }
      
      const result = await fn.apply(store, args)
      cache.set(key, { data: result, timestamp: Date.now() })
      
      return result
    }
  }
}

// Store 事件系统
class StoreEventBus {
  private events: Map<string, Function[]> = new Map()
  
  /**
   * 监听事件
   */
  on(event: string, callback: Function) {
    if (!this.events.has(event)) {
      this.events.set(event, [])
    }
    this.events.get(event)!.push(callback)
  }
  
  /**
   * 移除事件监听
   */
  off(event: string, callback?: Function) {
    if (!this.events.has(event)) return
    
    if (callback) {
      const callbacks = this.events.get(event)!
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    } else {
      this.events.delete(event)
    }
  }
  
  /**
   * 触发事件
   */
  emit(event: string, ...args: any[]) {
    if (!this.events.has(event)) return
    
    const callbacks = this.events.get(event)!
    callbacks.forEach(callback => {
      try {
        callback(...args)
      } catch (error) {
        console.error(`[StoreEventBus] Error in event handler for ${event}:`, error)
      }
    })
  }
}

// 导出事件总线实例
export const storeEventBus = new StoreEventBus()

// Store 管理器
export class StoreManager {
  private stores: Map<string, any> = new Map()
  
  /**
   * 注册 store
   */
  register(name: string, store: any) {
    this.stores.set(name, store)
    storeEventBus.emit('store:registered', name, store)
  }
  
  /**
   * 获取 store
   */
  get(name: string) {
    return this.stores.get(name)
  }
  
  /**
   * 重置所有 store
   */
  resetAll() {
    this.stores.forEach((store, name) => {
      if (typeof store.$reset === 'function') {
        store.$reset()
        storeEventBus.emit('store:reset', name)
      }
    })
  }
}

// 导出 store 管理器实例
export const storeManager = new StoreManager()

// 安装函数
export function setupStore(app: App) {
  app.use(pinia)
  
  // 在开发环境下添加调试信息
  if (import.meta.env.DEV) {
    // 添加全局属性用于调试
    app.config.globalProperties.$stores = storeManager
    
    // 监听 store 事件
    storeEventBus.on('store:registered', (name: string) => {
      console.log(`[Store] Registered: ${name}`)
    })
  }
  
  return pinia
}

export default pinia