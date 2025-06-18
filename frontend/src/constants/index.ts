// 常量定义主入口文件
// 统一管理应用常量

// 导出所有常量模块
// export * from './api'
// export * from './auth'
// export * from './routes'
// export * from './storage'
// export * from './upload'
// export * from './theme'
// export * from './i18n'
// export * from './status'
// export * from './errors'
// export * from './events'
// export * from './permissions'
// export * from './roles'
// export * from './menus'
// export * from './notifications'
// export * from './charts'
// export * from './forms'
// export * from './tables'
// export * from './search'
// export * from './knowledge'
// export * from './documents'
// export * from './system'

// 应用基础常量
export const APP_CONSTANTS = {
  // 应用信息
  NAME: 'ERAG',
  FULL_NAME: 'Enterprise RAG System',
  VERSION: '1.0.0',
  DESCRIPTION: 'Enterprise Retrieval-Augmented Generation System',
  AUTHOR: 'ERAG Team',
  COPYRIGHT: '© 2025 ERAG Team. All rights reserved.',
  
  // 构建信息
  BUILD_TIME: new Date().toISOString(),
  BUILD_VERSION: process.env.NODE_ENV === 'production' ? '1.0.0' : 'dev',
  
  // 环境信息
  ENV: {
    DEVELOPMENT: 'development',
    PRODUCTION: 'production',
    TEST: 'test',
    STAGING: 'staging'
  },
  
  // 平台信息
  PLATFORM: {
    WEB: 'web',
    MOBILE: 'mobile',
    DESKTOP: 'desktop',
    TABLET: 'tablet'
  },
  
  // 浏览器信息
  BROWSER: {
    CHROME: 'chrome',
    FIREFOX: 'firefox',
    SAFARI: 'safari',
    EDGE: 'edge',
    IE: 'ie',
    OPERA: 'opera'
  }
} as const

// HTTP 状态码常量
export const HTTP_STATUS = {
  // 成功状态码
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,
  
  // 重定向状态码
  MOVED_PERMANENTLY: 301,
  FOUND: 302,
  NOT_MODIFIED: 304,
  
  // 客户端错误状态码
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  METHOD_NOT_ALLOWED: 405,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  
  // 服务器错误状态码
  INTERNAL_SERVER_ERROR: 500,
  NOT_IMPLEMENTED: 501,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504
} as const

// HTTP 方法常量
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  PATCH: 'PATCH',
  DELETE: 'DELETE',
  HEAD: 'HEAD',
  OPTIONS: 'OPTIONS'
} as const

// 内容类型常量
export const CONTENT_TYPES = {
  JSON: 'application/json',
  FORM_DATA: 'multipart/form-data',
  FORM_URLENCODED: 'application/x-www-form-urlencoded',
  TEXT_PLAIN: 'text/plain',
  TEXT_HTML: 'text/html',
  TEXT_XML: 'text/xml',
  APPLICATION_XML: 'application/xml',
  APPLICATION_PDF: 'application/pdf',
  APPLICATION_ZIP: 'application/zip',
  IMAGE_JPEG: 'image/jpeg',
  IMAGE_PNG: 'image/png',
  IMAGE_GIF: 'image/gif',
  IMAGE_SVG: 'image/svg+xml'
} as const

// 文件类型常量
export const FILE_TYPES = {
  // 文档类型
  DOCUMENT: {
    PDF: 'pdf',
    DOC: 'doc',
    DOCX: 'docx',
    TXT: 'txt',
    RTF: 'rtf',
    ODT: 'odt'
  },
  
  // 图片类型
  IMAGE: {
    JPEG: 'jpeg',
    JPG: 'jpg',
    PNG: 'png',
    GIF: 'gif',
    SVG: 'svg',
    WEBP: 'webp',
    BMP: 'bmp',
    ICO: 'ico'
  },
  
  // 音频类型
  AUDIO: {
    MP3: 'mp3',
    WAV: 'wav',
    OGG: 'ogg',
    AAC: 'aac',
    FLAC: 'flac'
  },
  
  // 视频类型
  VIDEO: {
    MP4: 'mp4',
    AVI: 'avi',
    MOV: 'mov',
    WMV: 'wmv',
    FLV: 'flv',
    WEBM: 'webm'
  },
  
  // 压缩文件类型
  ARCHIVE: {
    ZIP: 'zip',
    RAR: 'rar',
    TAR: 'tar',
    GZ: 'gz',
    BZ2: 'bz2',
    '7Z': '7z'
  },
  
  // 代码文件类型
  CODE: {
    JS: 'js',
    TS: 'ts',
    JSX: 'jsx',
    TSX: 'tsx',
    VUE: 'vue',
    HTML: 'html',
    CSS: 'css',
    SCSS: 'scss',
    LESS: 'less',
    JSON: 'json',
    XML: 'xml',
    YAML: 'yaml',
    MD: 'md'
  }
} as const

// 正则表达式常量
export const REGEX_PATTERNS = {
  // 邮箱
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  
  // 手机号（中国）
  PHONE_CN: /^1[3-9]\d{9}$/,
  
  // 身份证号（中国）
  ID_CARD_CN: /^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/,
  
  // 密码（至少8位，包含大小写字母和数字）
  PASSWORD_STRONG: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$/,
  
  // URL
  URL: /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/,
  
  // IPv4 地址
  IPV4: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
  
  // IPv6 地址
  IPV6: /^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$/,
  
  // UUID
  UUID: /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  
  // 十六进制颜色
  HEX_COLOR: /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/,
  
  // 中文字符
  CHINESE: /[\u4e00-\u9fa5]/,
  
  // 英文字符
  ENGLISH: /^[a-zA-Z]+$/,
  
  // 数字
  NUMBER: /^\d+$/,
  
  // 小数
  DECIMAL: /^\d+\.\d+$/,
  
  // 正整数
  POSITIVE_INTEGER: /^[1-9]\d*$/,
  
  // 非负整数
  NON_NEGATIVE_INTEGER: /^\d+$/,
  
  // 银行卡号
  BANK_CARD: /^[1-9]\d{12,18}$/,
  
  // 邮政编码（中国）
  POSTAL_CODE_CN: /^[1-9]\d{5}$/
} as const

// 时间常量
export const TIME_CONSTANTS = {
  // 毫秒
  MILLISECOND: 1,
  SECOND: 1000,
  MINUTE: 60 * 1000,
  HOUR: 60 * 60 * 1000,
  DAY: 24 * 60 * 60 * 1000,
  WEEK: 7 * 24 * 60 * 60 * 1000,
  MONTH: 30 * 24 * 60 * 60 * 1000,
  YEAR: 365 * 24 * 60 * 60 * 1000,
  
  // 格式化字符串
  FORMATS: {
    DATE: 'YYYY-MM-DD',
    TIME: 'HH:mm:ss',
    DATETIME: 'YYYY-MM-DD HH:mm:ss',
    DATETIME_MINUTE: 'YYYY-MM-DD HH:mm',
    ISO: 'YYYY-MM-DDTHH:mm:ss.SSSZ',
    TIMESTAMP: 'X',
    RELATIVE: 'fromNow'
  },
  
  // 时区
  TIMEZONES: {
    UTC: 'UTC',
    BEIJING: 'Asia/Shanghai',
    TOKYO: 'Asia/Tokyo',
    NEW_YORK: 'America/New_York',
    LONDON: 'Europe/London',
    PARIS: 'Europe/Paris'
  }
} as const

// 尺寸常量
export const SIZE_CONSTANTS = {
  // 字节单位
  BYTE: 1,
  KB: 1024,
  MB: 1024 * 1024,
  GB: 1024 * 1024 * 1024,
  TB: 1024 * 1024 * 1024 * 1024,
  
  // 像素单位
  PX: 'px',
  EM: 'em',
  REM: 'rem',
  VW: 'vw',
  VH: 'vh',
  PERCENT: '%',
  
  // 响应式断点
  BREAKPOINTS: {
    XS: 480,
    SM: 576,
    MD: 768,
    LG: 992,
    XL: 1200,
    XXL: 1600
  },
  
  // 组件尺寸
  COMPONENT_SIZES: {
    MINI: 'mini',
    SMALL: 'small',
    MEDIUM: 'medium',
    LARGE: 'large'
  }
} as const

// 颜色常量
export const COLOR_CONSTANTS = {
  // 主题色
  PRIMARY: '#1890ff',
  SUCCESS: '#52c41a',
  WARNING: '#faad14',
  ERROR: '#f5222d',
  INFO: '#1890ff',
  
  // 中性色
  WHITE: '#ffffff',
  BLACK: '#000000',
  GRAY: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#eeeeee',
    300: '#e0e0e0',
    400: '#bdbdbd',
    500: '#9e9e9e',
    600: '#757575',
    700: '#616161',
    800: '#424242',
    900: '#212121'
  },
  
  // 透明度
  OPACITY: {
    TRANSPARENT: 'transparent',
    SEMI_TRANSPARENT: 'rgba(0, 0, 0, 0.5)',
    LIGHT: 'rgba(255, 255, 255, 0.1)',
    MEDIUM: 'rgba(255, 255, 255, 0.5)',
    HEAVY: 'rgba(255, 255, 255, 0.9)'
  }
} as const

// 动画常量
export const ANIMATION_CONSTANTS = {
  // 持续时间
  DURATION: {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500,
    SLOWER: 1000
  },
  
  // 缓动函数
  EASING: {
    LINEAR: 'linear',
    EASE: 'ease',
    EASE_IN: 'ease-in',
    EASE_OUT: 'ease-out',
    EASE_IN_OUT: 'ease-in-out',
    CUBIC_BEZIER: 'cubic-bezier(0.4, 0, 0.2, 1)'
  },
  
  // 动画类型
  TYPES: {
    FADE: 'fade',
    SLIDE: 'slide',
    ZOOM: 'zoom',
    FLIP: 'flip',
    BOUNCE: 'bounce',
    SHAKE: 'shake',
    PULSE: 'pulse',
    ROTATE: 'rotate'
  }
} as const

// Z-Index 常量
export const Z_INDEX_CONSTANTS = {
  DROPDOWN: 1000,
  STICKY: 1020,
  FIXED: 1030,
  MODAL_BACKDROP: 1040,
  MODAL: 1050,
  POPOVER: 1060,
  TOOLTIP: 1070,
  NOTIFICATION: 1080,
  LOADING: 1090,
  MAX: 2147483647
} as const

// 键盘按键常量
export const KEY_CODES = {
  BACKSPACE: 8,
  TAB: 9,
  ENTER: 13,
  SHIFT: 16,
  CTRL: 17,
  ALT: 18,
  PAUSE: 19,
  CAPS_LOCK: 20,
  ESCAPE: 27,
  SPACE: 32,
  PAGE_UP: 33,
  PAGE_DOWN: 34,
  END: 35,
  HOME: 36,
  LEFT: 37,
  UP: 38,
  RIGHT: 39,
  DOWN: 40,
  INSERT: 45,
  DELETE: 46,
  F1: 112,
  F2: 113,
  F3: 114,
  F4: 115,
  F5: 116,
  F6: 117,
  F7: 118,
  F8: 119,
  F9: 120,
  F10: 121,
  F11: 122,
  F12: 123
} as const

// 键盘按键名称常量
export const KEY_NAMES = {
  BACKSPACE: 'Backspace',
  TAB: 'Tab',
  ENTER: 'Enter',
  SHIFT: 'Shift',
  CTRL: 'Control',
  ALT: 'Alt',
  ESCAPE: 'Escape',
  SPACE: ' ',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_UP: 'ArrowUp',
  ARROW_RIGHT: 'ArrowRight',
  ARROW_DOWN: 'ArrowDown',
  DELETE: 'Delete',
  HOME: 'Home',
  END: 'End',
  PAGE_UP: 'PageUp',
  PAGE_DOWN: 'PageDown'
} as const

// 存储类型常量
export const STORAGE_TYPES = {
  LOCAL: 'localStorage',
  SESSION: 'sessionStorage',
  COOKIE: 'cookie',
  INDEXED_DB: 'indexedDB',
  MEMORY: 'memory'
} as const

// 网络状态常量
export const NETWORK_STATUS = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  SLOW: 'slow',
  FAST: 'fast'
} as const

// 设备类型常量
export const DEVICE_TYPES = {
  MOBILE: 'mobile',
  TABLET: 'tablet',
  DESKTOP: 'desktop',
  TV: 'tv',
  WATCH: 'watch'
} as const

// 操作系统常量
export const OS_TYPES = {
  WINDOWS: 'windows',
  MACOS: 'macos',
  LINUX: 'linux',
  ANDROID: 'android',
  IOS: 'ios',
  UNKNOWN: 'unknown'
} as const

// 常量工具函数
export const ConstantUtils = {
  // 获取常量值
  getValue(obj: any, path: string): any {
    const keys = path.split('.')
    let value = obj
    
    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key]
      } else {
        return undefined
      }
    }
    
    return value
  },
  
  // 检查常量是否存在
  hasValue(obj: any, path: string): boolean {
    return this.getValue(obj, path) !== undefined
  },
  
  // 获取所有常量键
  getKeys(obj: any): string[] {
    const keys: string[] = []
    
    function traverse(current: any, prefix = '') {
      for (const key in current) {
        const fullKey = prefix ? `${prefix}.${key}` : key
        if (typeof current[key] === 'object' && current[key] !== null) {
          traverse(current[key], fullKey)
        } else {
          keys.push(fullKey)
        }
      }
    }
    
    traverse(obj)
    return keys
  },
  
  // 获取所有常量值
  getValues(obj: any): any[] {
    const values: any[] = []
    
    function traverse(current: any) {
      for (const key in current) {
        if (typeof current[key] === 'object' && current[key] !== null) {
          traverse(current[key])
        } else {
          values.push(current[key])
        }
      }
    }
    
    traverse(obj)
    return values
  },
  
  // 反向查找常量
  findKey(obj: any, value: any): string | undefined {
    function traverse(current: any, prefix = ''): string | undefined {
      for (const key in current) {
        const fullKey = prefix ? `${prefix}.${key}` : key
        if (typeof current[key] === 'object' && current[key] !== null) {
          const result = traverse(current[key], fullKey)
          if (result) return result
        } else if (current[key] === value) {
          return fullKey
        }
      }
      return undefined
    }
    
    return traverse(obj)
  },
  
  // 冻结常量对象
  freeze(obj: any): any {
    Object.freeze(obj)
    
    for (const key in obj) {
      if (typeof obj[key] === 'object' && obj[key] !== null) {
        this.freeze(obj[key])
      }
    }
    
    return obj
  },
  
  // 验证常量值
  validate(obj: any, rules: any): boolean {
    for (const key in rules) {
      const value = this.getValue(obj, key)
      const rule = rules[key]
      
      if (rule.required && value === undefined) {
        return false
      }
      
      if (rule.type && typeof value !== rule.type) {
        return false
      }
      
      if (rule.enum && !rule.enum.includes(value)) {
        return false
      }
    }
    
    return true
  }
}

// 冻结所有常量对象
ConstantUtils.freeze(APP_CONSTANTS)
ConstantUtils.freeze(HTTP_STATUS)
ConstantUtils.freeze(HTTP_METHODS)
ConstantUtils.freeze(CONTENT_TYPES)
ConstantUtils.freeze(FILE_TYPES)
ConstantUtils.freeze(REGEX_PATTERNS)
ConstantUtils.freeze(TIME_CONSTANTS)
ConstantUtils.freeze(SIZE_CONSTANTS)
ConstantUtils.freeze(COLOR_CONSTANTS)
ConstantUtils.freeze(ANIMATION_CONSTANTS)
ConstantUtils.freeze(Z_INDEX_CONSTANTS)
ConstantUtils.freeze(KEY_CODES)
ConstantUtils.freeze(KEY_NAMES)
ConstantUtils.freeze(STORAGE_TYPES)
ConstantUtils.freeze(NETWORK_STATUS)
ConstantUtils.freeze(DEVICE_TYPES)
ConstantUtils.freeze(OS_TYPES)

// 导出默认常量集合
export default {
  APP: APP_CONSTANTS,
  HTTP_STATUS,
  HTTP_METHODS,
  CONTENT_TYPES,
  FILE_TYPES,
  REGEX: REGEX_PATTERNS,
  TIME: TIME_CONSTANTS,
  SIZE: SIZE_CONSTANTS,
  COLOR: COLOR_CONSTANTS,
  ANIMATION: ANIMATION_CONSTANTS,
  Z_INDEX: Z_INDEX_CONSTANTS,
  KEY_CODES,
  KEY_NAMES,
  STORAGE: STORAGE_TYPES,
  NETWORK: NETWORK_STATUS,
  DEVICE: DEVICE_TYPES,
  OS: OS_TYPES
}