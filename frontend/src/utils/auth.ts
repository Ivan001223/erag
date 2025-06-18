import Cookies from 'js-cookie'
import { encrypt, decrypt } from './crypto'

// Token相关常量
const TOKEN_KEY = 'erag_token'
const REFRESH_TOKEN_KEY = 'erag_refresh_token'
const USER_INFO_KEY = 'erag_user_info'
const PERMISSIONS_KEY = 'erag_permissions'
const REMEMBER_ME_KEY = 'erag_remember_me'

// Token配置
interface TokenConfig {
  domain?: string
  secure?: boolean
  sameSite?: 'strict' | 'lax' | 'none'
  expires?: number // 天数
}

// 默认配置
const defaultConfig: TokenConfig = {
  secure: location.protocol === 'https:',
  sameSite: 'lax',
  expires: 7 // 7天
}

/**
 * 获取Token
 * @returns Token字符串或null
 */
export const getToken = (): string | null => {
  try {
    // 优先从Cookie获取
    let token = Cookies.get(TOKEN_KEY)
    
    // 如果Cookie中没有，从localStorage获取
    if (!token) {
      token = localStorage.getItem(TOKEN_KEY)
    }
    
    // 如果token存在且加密，则解密
    if (token && token.startsWith('encrypted:')) {
      token = decrypt(token.replace('encrypted:', ''))
    }
    
    return token || null
  } catch (error) {
    console.error('获取Token失败:', error)
    return null
  }
}

/**
 * 设置Token
 * @param token Token字符串
 * @param config Token配置
 * @param remember 是否记住登录状态
 */
export const setToken = (token: string, config?: TokenConfig, remember = false): string => {
  try {
    const finalConfig = { ...defaultConfig, ...config }
    
    // 加密token
    const encryptedToken = `encrypted:${encrypt(token)}`
    
    if (remember) {
      // 记住登录状态，使用Cookie存储
      Cookies.set(TOKEN_KEY, encryptedToken, {
        expires: finalConfig.expires,
        domain: finalConfig.domain,
        secure: finalConfig.secure,
        sameSite: finalConfig.sameSite
      })
      
      // 标记记住状态
      localStorage.setItem(REMEMBER_ME_KEY, 'true')
    } else {
      // 不记住登录状态，使用sessionStorage
      sessionStorage.setItem(TOKEN_KEY, encryptedToken)
      localStorage.removeItem(REMEMBER_ME_KEY)
    }
    
    // 同时在localStorage中保存一份（用于跨标签页同步）
    localStorage.setItem(TOKEN_KEY, encryptedToken)
    
    return token
  } catch (error) {
    console.error('设置Token失败:', error)
    return token
  }
}

/**
 * 移除Token
 */
export const removeToken = (): void => {
  try {
    // 移除Cookie
    Cookies.remove(TOKEN_KEY)
    
    // 移除localStorage
    localStorage.removeItem(TOKEN_KEY)
    
    // 移除sessionStorage
    sessionStorage.removeItem(TOKEN_KEY)
    
    // 移除记住状态
    localStorage.removeItem(REMEMBER_ME_KEY)
  } catch (error) {
    console.error('移除Token失败:', error)
  }
}

/**
 * 获取刷新Token
 * @returns 刷新Token字符串或null
 */
export const getRefreshToken = (): string | null => {
  try {
    let refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    
    if (refreshToken && refreshToken.startsWith('encrypted:')) {
      refreshToken = decrypt(refreshToken.replace('encrypted:', ''))
    }
    
    return refreshToken
  } catch (error) {
    console.error('获取刷新Token失败:', error)
    return null
  }
}

/**
 * 设置刷新Token
 * @param refreshToken 刷新Token字符串
 */
export const setRefreshToken = (refreshToken: string): void => {
  try {
    const encryptedToken = `encrypted:${encrypt(refreshToken)}`
    localStorage.setItem(REFRESH_TOKEN_KEY, encryptedToken)
  } catch (error) {
    console.error('设置刷新Token失败:', error)
  }
}

/**
 * 移除刷新Token
 */
export const removeRefreshToken = (): void => {
  try {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  } catch (error) {
    console.error('移除刷新Token失败:', error)
  }
}

/**
 * 获取用户信息
 * @returns 用户信息对象或null
 */
export const getUserInfo = (): any => {
  try {
    const userInfo = localStorage.getItem(USER_INFO_KEY)
    return userInfo ? JSON.parse(userInfo) : null
  } catch (error) {
    console.error('获取用户信息失败:', error)
    return null
  }
}

/**
 * 设置用户信息
 * @param userInfo 用户信息对象
 */
export const setUserInfo = (userInfo: any): void => {
  try {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo))
  } catch (error) {
    console.error('设置用户信息失败:', error)
  }
}

/**
 * 移除用户信息
 */
export const removeUserInfo = (): void => {
  try {
    localStorage.removeItem(USER_INFO_KEY)
  } catch (error) {
    console.error('移除用户信息失败:', error)
  }
}

/**
 * 获取用户权限
 * @returns 权限数组或空数组
 */
export const getPermissions = (): string[] => {
  try {
    const permissions = localStorage.getItem(PERMISSIONS_KEY)
    return permissions ? JSON.parse(permissions) : []
  } catch (error) {
    console.error('获取用户权限失败:', error)
    return []
  }
}

/**
 * 设置用户权限
 * @param permissions 权限数组
 */
export const setPermissions = (permissions: string[]): void => {
  try {
    localStorage.setItem(PERMISSIONS_KEY, JSON.stringify(permissions))
  } catch (error) {
    console.error('设置用户权限失败:', error)
  }
}

/**
 * 移除用户权限
 */
export const removePermissions = (): void => {
  try {
    localStorage.removeItem(PERMISSIONS_KEY)
  } catch (error) {
    console.error('移除用户权限失败:', error)
  }
}

/**
 * 检查是否已登录
 * @returns 是否已登录
 */
export const isLoggedIn = (): boolean => {
  const token = getToken()
  return !!token && !isTokenExpired(token)
}

/**
 * 检查Token是否过期
 * @param token Token字符串
 * @returns 是否过期
 */
export const isTokenExpired = (token: string): boolean => {
  try {
    if (!token) return true
    
    // 解析JWT token
    const payload = parseJWT(token)
    if (!payload || !payload.exp) return true
    
    // 检查是否过期（提前5分钟判断为过期）
    const currentTime = Math.floor(Date.now() / 1000)
    const bufferTime = 5 * 60 // 5分钟缓冲时间
    
    return payload.exp < (currentTime + bufferTime)
  } catch (error) {
    console.error('检查Token过期失败:', error)
    return true
  }
}

/**
 * 解析JWT Token
 * @param token JWT Token字符串
 * @returns 解析后的payload或null
 */
export const parseJWT = (token: string): any => {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    
    return JSON.parse(decoded)
  } catch (error) {
    console.error('解析JWT Token失败:', error)
    return null
  }
}

/**
 * 获取Token剩余时间（秒）
 * @param token Token字符串
 * @returns 剩余时间（秒）
 */
export const getTokenRemainingTime = (token: string): number => {
  try {
    const payload = parseJWT(token)
    if (!payload || !payload.exp) return 0
    
    const currentTime = Math.floor(Date.now() / 1000)
    const remainingTime = payload.exp - currentTime
    
    return Math.max(0, remainingTime)
  } catch (error) {
    console.error('获取Token剩余时间失败:', error)
    return 0
  }
}

/**
 * 检查是否记住登录状态
 * @returns 是否记住登录状态
 */
export const isRememberMe = (): boolean => {
  return localStorage.getItem(REMEMBER_ME_KEY) === 'true'
}

/**
 * 清除所有认证信息
 */
export const clearAuth = (): void => {
  removeToken()
  removeRefreshToken()
  removeUserInfo()
  removePermissions()
}

/**
 * 检查用户是否有指定权限
 * @param permission 权限代码
 * @returns 是否有权限
 */
export const hasPermission = (permission: string): boolean => {
  const permissions = getPermissions()
  return permissions.includes(permission) || permissions.includes('*')
}

/**
 * 检查用户是否有任一权限
 * @param permissions 权限代码数组
 * @returns 是否有任一权限
 */
export const hasAnyPermission = (permissions: string[]): boolean => {
  return permissions.some(permission => hasPermission(permission))
}

/**
 * 检查用户是否有所有权限
 * @param permissions 权限代码数组
 * @returns 是否有所有权限
 */
export const hasAllPermissions = (permissions: string[]): boolean => {
  return permissions.every(permission => hasPermission(permission))
}

/**
 * 检查用户角色
 * @param role 角色代码
 * @returns 是否有该角色
 */
export const hasRole = (role: string): boolean => {
  const userInfo = getUserInfo()
  if (!userInfo || !userInfo.roles) return false
  
  return userInfo.roles.includes(role) || userInfo.roles.includes('admin')
}

/**
 * 检查用户是否有任一角色
 * @param roles 角色代码数组
 * @returns 是否有任一角色
 */
export const hasAnyRole = (roles: string[]): boolean => {
  return roles.some(role => hasRole(role))
}

/**
 * 检查用户是否有所有角色
 * @param roles 角色代码数组
 * @returns 是否有所有角色
 */
export const hasAllRoles = (roles: string[]): boolean => {
  return roles.every(role => hasRole(role))
}

/**
 * 监听Token变化
 * @param callback 回调函数
 * @returns 取消监听函数
 */
export const watchToken = (callback: (token: string | null) => void): (() => void) => {
  const handleStorageChange = (event: StorageEvent) => {
    if (event.key === TOKEN_KEY) {
      const token = getToken()
      callback(token)
    }
  }
  
  window.addEventListener('storage', handleStorageChange)
  
  return () => {
    window.removeEventListener('storage', handleStorageChange)
  }
}

/**
 * 自动刷新Token
 * @param refreshCallback 刷新Token的回调函数
 * @returns 取消自动刷新函数
 */
export const autoRefreshToken = (refreshCallback: () => Promise<void>): (() => void) => {
  let timer: NodeJS.Timeout | null = null
  
  const scheduleRefresh = () => {
    const token = getToken()
    if (!token) return
    
    const remainingTime = getTokenRemainingTime(token)
    
    // 在Token过期前10分钟刷新
    const refreshTime = Math.max(0, remainingTime - 10 * 60) * 1000
    
    if (timer) {
      clearTimeout(timer)
    }
    
    timer = setTimeout(async () => {
      try {
        await refreshCallback()
        scheduleRefresh() // 刷新成功后重新调度
      } catch (error) {
        console.error('自动刷新Token失败:', error)
      }
    }, refreshTime)
  }
  
  scheduleRefresh()
  
  return () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }
}