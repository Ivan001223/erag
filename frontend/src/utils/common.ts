import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import type { MessageOptions, NotificationOptions } from 'element-plus'

/**
 * 防抖函数
 * @param func 要防抖的函数
 * @param wait 等待时间（毫秒）
 * @param immediate 是否立即执行
 * @returns 防抖后的函数
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate = false
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout | null = null
  
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      if (!immediate) func(...args)
    }
    
    const callNow = immediate && !timeout
    
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(later, wait)
    
    if (callNow) func(...args)
  }
}

/**
 * 节流函数
 * @param func 要节流的函数
 * @param limit 时间间隔（毫秒）
 * @returns 节流后的函数
 */
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean
  
  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

/**
 * 深拷贝
 * @param obj 要拷贝的对象
 * @returns 拷贝后的对象
 */
export const deepClone = <T>(obj: T): T => {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T
  }
  
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as unknown as T
  }
  
  if (typeof obj === 'object') {
    const clonedObj = {} as { [key: string]: any }
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj as T
  }
  
  return obj
}

/**
 * 格式化文件大小
 * @param bytes 字节数
 * @param decimals 小数位数
 * @returns 格式化后的文件大小
 */
export const formatFileSize = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

/**
 * 格式化数字
 * @param num 数字
 * @param options 格式化选项
 * @returns 格式化后的数字字符串
 */
export const formatNumber = (
  num: number,
  options: {
    decimals?: number
    separator?: string
    prefix?: string
    suffix?: string
  } = {}
): string => {
  const { decimals = 0, separator = ',', prefix = '', suffix = '' } = options
  
  const parts = num.toFixed(decimals).split('.')
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, separator)
  
  return prefix + parts.join('.') + suffix
}

/**
 * 格式化日期
 * @param date 日期
 * @param format 格式字符串
 * @returns 格式化后的日期字符串
 */
export const formatDate = (date: Date | string | number, format = 'YYYY-MM-DD HH:mm:ss'): string => {
  const d = new Date(date)
  
  if (isNaN(d.getTime())) {
    return ''
  }
  
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 相对时间格式化
 * @param date 日期
 * @returns 相对时间字符串
 */
export const formatRelativeTime = (date: Date | string | number): string => {
  const now = new Date()
  const target = new Date(date)
  const diff = now.getTime() - target.getTime()
  
  const minute = 60 * 1000
  const hour = minute * 60
  const day = hour * 24
  const week = day * 7
  const month = day * 30
  const year = day * 365
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < week) {
    return `${Math.floor(diff / day)}天前`
  } else if (diff < month) {
    return `${Math.floor(diff / week)}周前`
  } else if (diff < year) {
    return `${Math.floor(diff / month)}个月前`
  } else {
    return `${Math.floor(diff / year)}年前`
  }
}

/**
 * 生成随机颜色
 * @param type 颜色类型
 * @returns 颜色字符串
 */
export const generateRandomColor = (type: 'hex' | 'rgb' | 'hsl' = 'hex'): string => {
  switch (type) {
    case 'hex':
      return '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0')
    
    case 'rgb':
      const r = Math.floor(Math.random() * 256)
      const g = Math.floor(Math.random() * 256)
      const b = Math.floor(Math.random() * 256)
      return `rgb(${r}, ${g}, ${b})`
    
    case 'hsl':
      const h = Math.floor(Math.random() * 360)
      const s = Math.floor(Math.random() * 100)
      const l = Math.floor(Math.random() * 100)
      return `hsl(${h}, ${s}%, ${l}%)`
    
    default:
      return '#000000'
  }
}

/**
 * 获取对比色
 * @param color 原始颜色（hex格式）
 * @returns 对比色
 */
export const getContrastColor = (color: string): string => {
  // 移除#号
  const hex = color.replace('#', '')
  
  // 转换为RGB
  const r = parseInt(hex.substr(0, 2), 16)
  const g = parseInt(hex.substr(2, 2), 16)
  const b = parseInt(hex.substr(4, 2), 16)
  
  // 计算亮度
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  
  // 返回对比色
  return brightness > 128 ? '#000000' : '#ffffff'
}

/**
 * 下载文件
 * @param url 文件URL
 * @param filename 文件名
 */
export const downloadFile = (url: string, filename?: string): void => {
  const link = document.createElement('a')
  link.href = url
  link.download = filename || 'download'
  link.style.display = 'none'
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

/**
 * 下载Blob数据
 * @param blob Blob数据
 * @param filename 文件名
 */
export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob)
  downloadFile(url, filename)
  URL.revokeObjectURL(url)
}

/**
 * 复制文本到剪贴板
 * @param text 要复制的文本
 * @returns Promise<boolean> 是否成功
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    } else {
      // 降级方案
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      
      const result = document.execCommand('copy')
      document.body.removeChild(textArea)
      
      return result
    }
  } catch (error) {
    console.error('复制到剪贴板失败:', error)
    return false
  }
}

/**
 * 获取URL参数
 * @param name 参数名
 * @param url URL字符串
 * @returns 参数值
 */
export const getUrlParam = (name: string, url?: string): string | null => {
  const targetUrl = url || window.location.href
  const urlObj = new URL(targetUrl)
  return urlObj.searchParams.get(name)
}

/**
 * 设置URL参数
 * @param params 参数对象
 * @param url URL字符串
 * @returns 新的URL字符串
 */
export const setUrlParams = (params: Record<string, string>, url?: string): string => {
  const targetUrl = url || window.location.href
  const urlObj = new URL(targetUrl)
  
  Object.entries(params).forEach(([key, value]) => {
    urlObj.searchParams.set(key, value)
  })
  
  return urlObj.toString()
}

/**
 * 移除URL参数
 * @param names 参数名数组
 * @param url URL字符串
 * @returns 新的URL字符串
 */
export const removeUrlParams = (names: string[], url?: string): string => {
  const targetUrl = url || window.location.href
  const urlObj = new URL(targetUrl)
  
  names.forEach(name => {
    urlObj.searchParams.delete(name)
  })
  
  return urlObj.toString()
}

/**
 * 检测设备类型
 * @returns 设备类型
 */
export const getDeviceType = (): 'mobile' | 'tablet' | 'desktop' => {
  const userAgent = navigator.userAgent.toLowerCase()
  
  if (/mobile|android|iphone|ipod|blackberry|iemobile|opera mini/i.test(userAgent)) {
    return 'mobile'
  }
  
  if (/tablet|ipad/i.test(userAgent)) {
    return 'tablet'
  }
  
  return 'desktop'
}

/**
 * 检测浏览器类型
 * @returns 浏览器信息
 */
export const getBrowserInfo = (): {
  name: string
  version: string
  engine: string
} => {
  const userAgent = navigator.userAgent
  
  let name = 'Unknown'
  let version = 'Unknown'
  let engine = 'Unknown'
  
  // 检测浏览器
  if (userAgent.includes('Chrome')) {
    name = 'Chrome'
    version = userAgent.match(/Chrome\/(\d+\.\d+)/)?.[1] || 'Unknown'
    engine = 'Blink'
  } else if (userAgent.includes('Firefox')) {
    name = 'Firefox'
    version = userAgent.match(/Firefox\/(\d+\.\d+)/)?.[1] || 'Unknown'
    engine = 'Gecko'
  } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
    name = 'Safari'
    version = userAgent.match(/Version\/(\d+\.\d+)/)?.[1] || 'Unknown'
    engine = 'WebKit'
  } else if (userAgent.includes('Edge')) {
    name = 'Edge'
    version = userAgent.match(/Edge\/(\d+\.\d+)/)?.[1] || 'Unknown'
    engine = 'EdgeHTML'
  }
  
  return { name, version, engine }
}

/**
 * 检测操作系统
 * @returns 操作系统名称
 */
export const getOperatingSystem = (): string => {
  const userAgent = navigator.userAgent
  
  if (userAgent.includes('Windows')) return 'Windows'
  if (userAgent.includes('Mac OS')) return 'macOS'
  if (userAgent.includes('Linux')) return 'Linux'
  if (userAgent.includes('Android')) return 'Android'
  if (userAgent.includes('iOS')) return 'iOS'
  
  return 'Unknown'
}

/**
 * 全屏操作
 */
export const fullscreen = {
  // 进入全屏
  enter: (element?: HTMLElement): Promise<void> => {
    const el = element || document.documentElement
    
    if (el.requestFullscreen) {
      return el.requestFullscreen()
    } else if ((el as any).webkitRequestFullscreen) {
      return (el as any).webkitRequestFullscreen()
    } else if ((el as any).msRequestFullscreen) {
      return (el as any).msRequestFullscreen()
    }
    
    return Promise.reject(new Error('Fullscreen not supported'))
  },
  
  // 退出全屏
  exit: (): Promise<void> => {
    if (document.exitFullscreen) {
      return document.exitFullscreen()
    } else if ((document as any).webkitExitFullscreen) {
      return (document as any).webkitExitFullscreen()
    } else if ((document as any).msExitFullscreen) {
      return (document as any).msExitFullscreen()
    }
    
    return Promise.reject(new Error('Exit fullscreen not supported'))
  },
  
  // 切换全屏
  toggle: (element?: HTMLElement): Promise<void> => {
    if (fullscreen.isActive()) {
      return fullscreen.exit()
    } else {
      return fullscreen.enter(element)
    }
  },
  
  // 检查是否全屏
  isActive: (): boolean => {
    return !!(document.fullscreenElement || 
             (document as any).webkitFullscreenElement || 
             (document as any).msFullscreenElement)
  }
}

/**
 * 消息提示封装
 */
export const message = {
  success: (msg: string, options?: MessageOptions) => {
    ElMessage.success({ message: msg, ...options })
  },
  
  error: (msg: string, options?: MessageOptions) => {
    ElMessage.error({ message: msg, ...options })
  },
  
  warning: (msg: string, options?: MessageOptions) => {
    ElMessage.warning({ message: msg, ...options })
  },
  
  info: (msg: string, options?: MessageOptions) => {
    ElMessage.info({ message: msg, ...options })
  }
}

/**
 * 通知提示封装
 */
export const notification = {
  success: (title: string, message?: string, options?: NotificationOptions) => {
    ElNotification.success({ title, message, ...options })
  },
  
  error: (title: string, message?: string, options?: NotificationOptions) => {
    ElNotification.error({ title, message, ...options })
  },
  
  warning: (title: string, message?: string, options?: NotificationOptions) => {
    ElNotification.warning({ title, message, ...options })
  },
  
  info: (title: string, message?: string, options?: NotificationOptions) => {
    ElNotification.info({ title, message, ...options })
  }
}

/**
 * 确认对话框
 * @param message 消息内容
 * @param title 标题
 * @param options 选项
 * @returns Promise<boolean>
 */
export const confirm = (
  message: string,
  title = '确认',
  options: any = {}
): Promise<boolean> => {
  return ElMessageBox.confirm(message, title, {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
    ...options
  }).then(() => true).catch(() => false)
}

/**
 * 数组去重
 * @param array 数组
 * @param key 对象数组的去重键
 * @returns 去重后的数组
 */
export const uniqueArray = <T>(array: T[], key?: keyof T): T[] => {
  if (!key) {
    return [...new Set(array)]
  }
  
  const seen = new Set()
  return array.filter(item => {
    const value = item[key]
    if (seen.has(value)) {
      return false
    }
    seen.add(value)
    return true
  })
}

/**
 * 数组分组
 * @param array 数组
 * @param key 分组键
 * @returns 分组后的对象
 */
export const groupBy = <T>(array: T[], key: keyof T): Record<string, T[]> => {
  return array.reduce((groups, item) => {
    const group = String(item[key])
    groups[group] = groups[group] || []
    groups[group].push(item)
    return groups
  }, {} as Record<string, T[]>)
}

/**
 * 数组排序
 * @param array 数组
 * @param key 排序键
 * @param order 排序顺序
 * @returns 排序后的数组
 */
export const sortBy = <T>(
  array: T[],
  key: keyof T,
  order: 'asc' | 'desc' = 'asc'
): T[] => {
  return [...array].sort((a, b) => {
    const aVal = a[key]
    const bVal = b[key]
    
    if (aVal < bVal) return order === 'asc' ? -1 : 1
    if (aVal > bVal) return order === 'asc' ? 1 : -1
    return 0
  })
}

/**
 * 树形数据扁平化
 * @param tree 树形数据
 * @param childrenKey 子节点键名
 * @returns 扁平化数组
 */
export const flattenTree = <T extends Record<string, any>>(
  tree: T[],
  childrenKey = 'children'
): T[] => {
  const result: T[] = []
  
  const flatten = (nodes: T[]) => {
    nodes.forEach(node => {
      result.push(node)
      if (node[childrenKey] && Array.isArray(node[childrenKey])) {
        flatten(node[childrenKey])
      }
    })
  }
  
  flatten(tree)
  return result
}

/**
 * 扁平数据转树形
 * @param array 扁平数组
 * @param options 配置选项
 * @returns 树形数据
 */
export const arrayToTree = <T extends Record<string, any>>(
  array: T[],
  options: {
    idKey?: string
    parentKey?: string
    childrenKey?: string
    rootValue?: any
  } = {}
): T[] => {
  const {
    idKey = 'id',
    parentKey = 'parentId',
    childrenKey = 'children',
    rootValue = null
  } = options
  
  const tree: T[] = []
  const map = new Map<any, T>()
  
  // 创建映射
  array.forEach(item => {
    map.set(item[idKey], { ...item, [childrenKey]: [] })
  })
  
  // 构建树形结构
  array.forEach(item => {
    const node = map.get(item[idKey])!
    const parentId = item[parentKey]
    
    if (parentId === rootValue) {
      tree.push(node)
    } else {
      const parent = map.get(parentId)
      if (parent) {
        parent[childrenKey].push(node)
      }
    }
  })
  
  return tree
}