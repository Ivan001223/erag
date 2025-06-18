/**
 * 本地存储工具函数
 */

/**
 * 存储类型
 */
export type StorageType = 'localStorage' | 'sessionStorage'

/**
 * 存储选项
 */
export interface StorageOptions {
  /** 过期时间（毫秒） */
  expires?: number
  /** 是否加密 */
  encrypt?: boolean
  /** 加密密钥 */
  secretKey?: string
}

/**
 * 存储数据结构
 */
interface StorageData<T = any> {
  /** 数据值 */
  value: T
  /** 创建时间 */
  timestamp: number
  /** 过期时间 */
  expires?: number
  /** 是否加密 */
  encrypted?: boolean
}

/**
 * 简单的加密/解密函数
 */
const simpleEncrypt = (text: string, key: string): string => {
  let result = ''
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(
      text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
    )
  }
  return btoa(result)
}

const simpleDecrypt = (encryptedText: string, key: string): string => {
  const text = atob(encryptedText)
  let result = ''
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(
      text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
    )
  }
  return result
}

/**
 * 存储工具类
 */
export class CustomStorage implements globalThis.Storage {
  private _storage: globalThis.Storage; // Renamed from storage
  public get length(): number {
    const keys = [];
    for (let i = 0; i < this._storage.length; i++) {
      const k = this._storage.key(i);
      if (k && k.startsWith(this.prefix)) {
        keys.push(k);
      }
    }
    return keys.length;
  }
  private prefix: string
  private defaultOptions: StorageOptions

  constructor(
    type: StorageType = 'localStorage',
    prefix = 'app_',
    defaultOptions: StorageOptions = {}
  ) {
    this._storage = type === 'localStorage' ? window.localStorage : window.sessionStorage; // Use renamed _storage
    this.prefix = prefix;
    this.defaultOptions = defaultOptions;
  }

  /**
   * 获取完整的键名
   * @param key 键名
   * @returns 完整键名
   */
  private getFullKey(key: string): string {
    return this.prefix + key
  }

  /**
   * 检查数据是否过期
   * @param data 存储数据
   * @returns 是否过期
   */
  private isExpired(data: StorageData): boolean {
    if (!data.expires) return false
    return Date.now() > data.expires
  }

  /**
   * 序列化数据
   * @param value 数据值
   * @param options 存储选项
   * @returns 序列化后的字符串
   */
  private serialize(value: any, options: StorageOptions): string {
    const data: StorageData = {
      value,
      timestamp: Date.now(),
      expires: options.expires ? Date.now() + options.expires : undefined,
      encrypted: options.encrypt
    }

    let serialized = JSON.stringify(data)

    if (options.encrypt && options.secretKey) {
      serialized = simpleEncrypt(serialized, options.secretKey)
    }

    return serialized
  }

  /**
   * 反序列化数据
   * @param serialized 序列化的字符串
   * @param options 存储选项
   * @returns 反序列化后的数据
   */
  private deserialize(serialized: string, options: StorageOptions): any {
    try {
      let dataString = serialized

      if (options.encrypt && options.secretKey) {
        dataString = simpleDecrypt(serialized, options.secretKey)
      }

      const data: StorageData = JSON.parse(dataString)

      if (this.isExpired(data)) {
        return null
      }

      return data.value
    } catch (error) {
      console.error('反序列化数据失败:', error)
      return null
    }
  }

  /**
   * 设置存储项
   * @param key 键名
   * @param value 值
   * @param options 存储选项
   */
  // Overload for Storage interface: setItem(key: string, value: string): void;
  setItem(key: string, value: string): void;
  // Generic overload with options
  setItem<T>(key: string, value: T, options?: StorageOptions): void;
  // Implementation
  setItem<T>(key: string, value: T | string, options: StorageOptions = {}): void {
    const mergedOptions = { ...this.defaultOptions, ...options }
    const fullKey = this.getFullKey(key)
    const serialized = this.serialize(value, mergedOptions)

    try {
      this._storage.setItem(fullKey, serialized) // Use renamed _storage
    } catch (error) {
      console.error('设置存储项失败:', error)
      // 如果存储空间不足，尝试清理过期数据
      // this.clearExpired() // Commented out as clearExpired is not part of the Storage interface and was causing an error. 
      // Consider implementing it if custom, or removing this call if it's a leftover.
      try {
        this._storage.setItem(fullKey, serialized) // Use renamed _storage
      } catch (retryError) {
        console.error('重试设置存储项失败:', retryError)
      }
    }
  }

  /**
   * 获取存储项
   * @param key 键名
   * @param defaultValue 默认值
   * @param options 存储选项
   * @returns 存储的值或默认值
   */
  // Overload for Storage interface: getItem(key: string): string | null;
  getItem(key: string): string | null;
  // Generic overload with options and defaultValue
  getItem<T>(key: string, defaultValue: T, options?: StorageOptions): T;
  getItem<T>(key: string, defaultValue?: T, options?: StorageOptions): T | string | null | undefined;
  // Implementation
  getItem<T>(key: string, defaultValue?: T, options: StorageOptions = {}): T | string | null | undefined {
    const mergedOptions = { ...this.defaultOptions, ...options }
    const fullKey = this.getFullKey(key)

    try {
      const serialized = this._storage.getItem(fullKey) // Use renamed _storage
      if (serialized === null) {
        return defaultValue
      }

      const value = this.deserialize(serialized, mergedOptions)
      if (value === null) {
        // 数据过期或解析失败，删除该项
        this.removeItem(key) // Corrected to use removeItem
        return defaultValue
      }

      return value
    } catch (error) {
      console.error('获取存储项失败:', error)
      return defaultValue
    }
  }

  /**
   * 删除存储项
   * @param key 键名
   */
  removeItem(key: string): void { // Renamed to removeItem
    const fullKey = this.getFullKey(key)
    this._storage.removeItem(fullKey) // Use renamed _storage
  }

  /**
   * 检查存储项是否存在
   * @param key 键名
   * @returns 是否存在
   */
  has(key: string): boolean {
    const fullKey = this.getFullKey(key)
    return this._storage.getItem(fullKey) !== null // Use renamed _storage
  }

  /**
   * 清空所有存储项（仅清空带前缀的）
   */
  clear(): void { // Stays as clear, part of Storage interface
    const keys = this.getPrefixedKeys(); // Use getPrefixedKeys for internal operations; // getKeys returns prefixed keys
    keys.forEach(prefixedKey => {
      this._storage.removeItem(prefixedKey); // Use renamed _storage to remove the actual key
    });
  }

  /**
   * 获取所有键名（仅返回带前缀的）
   * @returns 键名数组
   */
  // This method returns prefixed keys, as it was originally.
  // It's used internally by clear() and getAll().
  // If this is intended to be public and return non-prefixed keys, it needs adjustment.
  private getPrefixedKeys(): string[] {
    const keys: string[] = [];
    for (let i = 0; i < this._storage.length; i++) {
      const key = this._storage.key(i);
      if (key && key.startsWith(this.prefix)) {
        keys.push(key);
      }
    }
    return keys;
  }

  /**
   * 获取所有键名（仅返回不带前缀的键名）
   * @returns 键名数组
   */
  public getKeys(): string[] {
    return this.getPrefixedKeys().map(k => k.substring(this.prefix.length));
  }

  // Implementation for Storage.key(index: number)
  // Returns the name of the nth key in the list, or null if n is out of bounds.
  // This should refer to the keys managed by this CustomStorage instance (prefixed keys).
  public key(index: number): string | null {
    const prefixedKeys = this.getPrefixedKeys();
    if (index >= 0 && index < prefixedKeys.length) {
      // The Storage interface expects the actual key name if it were to be used with native getItem/setItem
      // However, our CustomStorage methods (getItem, setItem) expect non-prefixed keys.
      // For consistency with how our CustomStorage operates, let's return the non-prefixed key.
      return prefixedKeys[index].substring(this.prefix.length);
    }
    return null;
  }

  // clearExpired method needs to be defined if it's intended to be used.
  // For now, it's commented out where it was called to resolve the immediate error.
  // If clearExpired is a custom functionality, it should be implemented here.
  /*
  clearExpired(): void {
    const keys = this.getPrefixedKeys(); // Use getPrefixedKeys for internal operations;
    keys.forEach(fullKey => {
      try {
        const serialized = this._storage.getItem(fullKey) // Use renamed _storage;
        if (serialized) {
          const data: StorageData = JSON.parse(serialized);
          if (this.isExpired(data)) {
            this._storage.removeItem(fullKey) // Use renamed _storage;
          }
        }
      } catch (error) {
        this._storage.removeItem(fullKey) // Use renamed _storage;
      }
    });
  }
  */


  /**
   * 获取所有存储项
   * @returns 存储项对象
   */
  getAll(): Record<string, any> {
    const result: Record<string, any> = {}
    const keys = this.getPrefixedKeys(); // Use getPrefixedKeys for internal operations
    
    keys.forEach(fullKey => {
      const key = fullKey.replace(this.prefix, '')
      const value = this.getItem(key); // getItem expects non-prefixed key
      if (value !== undefined) {
        result[key] = value
      }
    })

    return result
  }

  /**
   * 清理过期数据
   */
  clearExpired(): void {
    const keys = this.getKeys()
    
    keys.forEach(fullKey => {
      try {
        const serialized = this._storage.getItem(fullKey) // Use renamed _storage
        if (serialized) {
          const data: StorageData = JSON.parse(serialized)
          if (this.isExpired(data)) {
            this._storage.removeItem(fullKey) // Use renamed _storage
          }
        }
      } catch (error) {
        // 如果解析失败，也删除该项
        this._storage.removeItem(fullKey) // Use renamed _storage
      }
    })
  }

  /**
   * 获取存储使用情况
   * @returns 存储使用情况
   */
  getUsage(): {
    used: number
    total: number
    percentage: number
    items: number
  } {
    let used = 0
    const keys = this.getKeys()
    
    keys.forEach(key => {
      const value = this._storage.getItem(key) // Use renamed _storage, key here is prefixedKey
      if (value) {
        used += value.length
      }
    })

    // 估算总容量（通常为5MB）
    const total = 5 * 1024 * 1024
    const percentage = (used / total) * 100

    return {
      used,
      total,
      percentage: Math.round(percentage * 100) / 100,
      items: keys.length
    }
  }

  /**
   * 导出数据
   * @returns 导出的数据
   */
  export(): string {
    const data = this.getAll()
    return JSON.stringify(data, null, 2)
  }

  /**
   * 导入数据
   * @param jsonString JSON字符串
   * @param overwrite 是否覆盖现有数据
   */
  import(jsonString: string, overwrite = false): void {
    try {
      const data = JSON.parse(jsonString)
      
      Object.entries(data).forEach(([key, value]) => {
        if (overwrite || !this.has(key)) {
          this.setItem(key, value) // Changed to setItem
        }
      })
    } catch (error) {
      console.error('导入数据失败:', error)
      throw new Error('无效的JSON格式')
    }
  }

  /**
   * 监听存储变化
   * @param callback 回调函数
   * @returns 取消监听的函数
   */
  watch(callback: (key: string, newValue: any, oldValue: any) => void): () => void {
    const handler = (event: Event) => { // Changed to Event to match addEventListener
      // Type assertion to avoid TS2339, as DOM StorageEvent doesn't have storageArea directly in all contexts
      // Also, ensure that the event is indeed a StorageEvent before accessing StorageEvent specific properties
      if (event instanceof StorageEvent && (event as any).storageArea === this._storage && // Use renamed _storage
          event.key && 
          event.key.startsWith(this.prefix)) { // Removed duplicated if condition
        const key = event.key.replace(this.prefix, '')
        const newValue = event.newValue ? this.deserialize(event.newValue, this.defaultOptions) : null
        const oldValue = event.oldValue ? this.deserialize(event.oldValue, this.defaultOptions) : null
        callback(key, newValue, oldValue)
      }
    }

    const eventHandler = handler as EventListener; // Use EventListener type
    window.addEventListener('storage', eventHandler);
    
    return () => {
      window.removeEventListener('storage', eventHandler);
    }; // Added semicolon for consistency
  }
}

/**
 * 默认的localStorage实例
 */
export const localStorage = new CustomStorage('localStorage', 'app_')

/**
 * 默认的sessionStorage实例
 */
export const sessionStorage = new CustomStorage('sessionStorage', 'app_')

/**
 * 用户相关的存储实例
 */
export const userStorage = new CustomStorage('localStorage', 'user_')

/**
 * 系统设置存储实例
 */
export const settingsStorage = new CustomStorage('localStorage', 'settings_')

/**
 * 缓存存储实例（带过期时间）
 */
export const cacheStorage = new CustomStorage('localStorage', 'cache_', {
  expires: 24 * 60 * 60 * 1000 // 24小时
})

/**
 * 安全存储实例（加密）
 */
export const secureStorage = new CustomStorage('localStorage', 'secure_', {
  encrypt: true,
  secretKey: 'your-secret-key' // 在实际项目中应该使用环境变量
})

/**
 * 便捷的存储函数
 */
export const storage = {
  /**
   * 设置本地存储
   */
  setLocal: <T>(key: string, value: T, options?: StorageOptions) => {
    localStorage.setItem(key, value, options) // Changed to setItem
  },

  /**
   * 获取本地存储
   */
  getLocal: <T>(key: string, defaultValue?: T, options?: StorageOptions): T | string | null | undefined => { // Adjusted return type
    return localStorage.getItem(key, defaultValue, options) // Changed to getItem
  },

  /**
   * 删除本地存储
   */
  removeLocal: (key: string) => {
    localStorage.removeItem(key) // Changed to removeItem
  },

  /**
   * 设置会话存储
   */
  setSession: <T>(key: string, value: T, options?: StorageOptions) => {
    sessionStorage.setItem(key, value, options) // Changed to setItem
  },

  /**
   * 获取会话存储
   */
  getSession: <T>(key: string, defaultValue?: T, options?: StorageOptions): T | string | null | undefined => { // Adjusted return type
    return sessionStorage.getItem(key, defaultValue, options) // Changed to getItem
  },

  /**
   * 删除会话存储
   */
  removeSession: (key: string) => {
    sessionStorage.removeItem(key) // Changed to removeItem
  },

  /**
   * 设置用户存储
   */
  setUser: <T>(key: string, value: T, options?: StorageOptions) => {
    userStorage.setItem(key, value, options) // Changed to setItem
  },

  /**
   * 获取用户存储
   */
  getUser: <T>(key: string, defaultValue?: T, options?: StorageOptions): T | string | null | undefined => { // Adjusted return type
    return userStorage.getItem(key, defaultValue, options) // Changed to getItem
  },

  /**
   * 删除用户存储
   */
  removeUser: (key: string) => {
    userStorage.removeItem(key) // Changed to removeItem
  },

  /**
   * 设置缓存
   */
  setCache: <T>(key: string, value: T, expires?: number) => {
    cacheStorage.setItem(key, value, { expires }) // Changed to setItem
  },

  /**
   * 获取缓存
   */
  getCache: <T>(key: string, defaultValue?: T): T | string | null | undefined => { // Adjusted return type
    return cacheStorage.getItem(key, defaultValue) // Changed to getItem
  },

  /**
   * 删除缓存
   */
  removeCache: (key: string) => {
    cacheStorage.removeItem(key) // Changed to removeItem
  },

  /**
   * 清理过期缓存
   */
  clearExpiredCache: () => {
    cacheStorage.clearExpired()
  },

  /**
   * 设置安全存储
   */
  setSecure: <T>(key: string, value: T, secretKey?: string) => {
    secureStorage.setItem(key, value, { encrypt: true, secretKey }) // Changed to setItem
  },

  /**
   * 获取安全存储
   */
  getSecure: <T>(key: string, defaultValue?: T, secretKey?: string): T | string | null | undefined => { // Adjusted return type
    return secureStorage.getItem(key, defaultValue, { encrypt: true, secretKey }) // Changed to getItem
  },

  /**
   * 删除安全存储
   */
  removeSecure: (key: string) => {
    secureStorage.removeItem(key) // Changed to removeItem
  }
}

/**
 * 存储事件类型
 */
export interface StorageEvent {
  key: string
  newValue: any
  oldValue: any
  timestamp: number
}

/**
 * 存储事件管理器
 */
export class StorageEventManager {
  private listeners: Map<string, ((event: StorageEvent) => void)[]> = new Map()

  /**
   * 添加监听器
   * @param key 键名
   * @param listener 监听器函数
   */
  on(key: string, listener: (event: StorageEvent) => void): void {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, [])
    }
    this.listeners.get(key)!.push(listener)
  }

  /**
   * 移除监听器
   * @param key 键名
   * @param listener 监听器函数
   */
  off(key: string, listener: (event: StorageEvent) => void): void {
    const listeners = this.listeners.get(key)
    if (listeners) {
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  /**
   * 触发事件
   * @param key 键名
   * @param newValue 新值
   * @param oldValue 旧值
   */
  emit(key: string, newValue: any, oldValue: any): void {
    const listeners = this.listeners.get(key)
    if (listeners) {
      const event: StorageEvent = {
        key,
        newValue,
        oldValue,
        timestamp: Date.now()
      }
      listeners.forEach(listener => listener(event))
    }
  }

  /**
   * 清空所有监听器
   */
  clear(): void {
    this.listeners.clear()
  }
}

/**
 * 默认的存储事件管理器实例
 */
export const storageEventManager = new StorageEventManager()