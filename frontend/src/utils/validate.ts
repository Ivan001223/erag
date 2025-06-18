/**
 * 表单验证工具函数
 */

/**
 * 验证邮箱格式
 * @param email 邮箱地址
 * @returns 是否有效
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * 验证手机号格式（中国大陆）
 * @param phone 手机号
 * @returns 是否有效
 */
export const isValidPhone = (phone: string): boolean => {
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(phone)
}

/**
 * 验证身份证号格式（中国大陆）
 * @param idCard 身份证号
 * @returns 是否有效
 */
export const isValidIdCard = (idCard: string): boolean => {
  const idCardRegex = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/
  return idCardRegex.test(idCard)
}

/**
 * 验证密码强度
 * @param password 密码
 * @param options 验证选项
 * @returns 验证结果
 */
export const validatePassword = (
  password: string,
  options: {
    minLength?: number
    maxLength?: number
    requireUppercase?: boolean
    requireLowercase?: boolean
    requireNumbers?: boolean
    requireSpecialChars?: boolean
    specialChars?: string
  } = {}
): {
  isValid: boolean
  strength: 'weak' | 'medium' | 'strong' | 'very-strong'
  errors: string[]
} => {
  const {
    minLength = 8,
    maxLength = 128,
    requireUppercase = true,
    requireLowercase = true,
    requireNumbers = true,
    requireSpecialChars = true,
    specialChars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
  } = options

  const errors: string[] = []
  let score = 0

  // 长度检查
  if (password.length < minLength) {
    errors.push(`密码长度至少${minLength}位`)
  } else if (password.length >= minLength) {
    score += 1
  }

  if (password.length > maxLength) {
    errors.push(`密码长度不能超过${maxLength}位`)
  }

  // 大写字母检查
  if (requireUppercase && !/[A-Z]/.test(password)) {
    errors.push('密码必须包含大写字母')
  } else if (/[A-Z]/.test(password)) {
    score += 1
  }

  // 小写字母检查
  if (requireLowercase && !/[a-z]/.test(password)) {
    errors.push('密码必须包含小写字母')
  } else if (/[a-z]/.test(password)) {
    score += 1
  }

  // 数字检查
  if (requireNumbers && !/\d/.test(password)) {
    errors.push('密码必须包含数字')
  } else if (/\d/.test(password)) {
    score += 1
  }

  // 特殊字符检查
  const specialCharsRegex = new RegExp(`[${specialChars.replace(/[\-\[\]{}()*+?.,\\^$|#\s]/g, '\\$&')}]`)
  if (requireSpecialChars && !specialCharsRegex.test(password)) {
    errors.push('密码必须包含特殊字符')
  } else if (specialCharsRegex.test(password)) {
    score += 1
  }

  // 额外强度检查
  if (password.length >= 12) score += 1
  if (/[A-Z].*[A-Z]/.test(password)) score += 1
  if (/\d.*\d/.test(password)) score += 1
  if (specialCharsRegex.test(password) && password.match(specialCharsRegex)?.length! > 1) score += 1

  // 计算强度
  let strength: 'weak' | 'medium' | 'strong' | 'very-strong'
  if (score < 3) {
    strength = 'weak'
  } else if (score < 5) {
    strength = 'medium'
  } else if (score < 7) {
    strength = 'strong'
  } else {
    strength = 'very-strong'
  }

  return {
    isValid: errors.length === 0,
    strength,
    errors
  }
}

/**
 * 验证URL格式
 * @param url URL地址
 * @returns 是否有效
 */
export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

/**
 * 验证IP地址格式
 * @param ip IP地址
 * @param version IP版本（4或6）
 * @returns 是否有效
 */
export const isValidIP = (ip: string, version?: 4 | 6): boolean => {
  if (version === 4) {
    const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
    return ipv4Regex.test(ip)
  }
  
  if (version === 6) {
    const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/
    return ipv6Regex.test(ip)
  }
  
  // 自动检测
  return isValidIP(ip, 4) || isValidIP(ip, 6)
}

/**
 * 验证MAC地址格式
 * @param mac MAC地址
 * @returns 是否有效
 */
export const isValidMAC = (mac: string): boolean => {
  const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/
  return macRegex.test(mac)
}

/**
 * 验证银行卡号格式
 * @param cardNumber 银行卡号
 * @returns 是否有效
 */
export const isValidBankCard = (cardNumber: string): boolean => {
  // 移除空格和连字符
  const cleanNumber = cardNumber.replace(/[\s-]/g, '')
  
  // 检查是否只包含数字
  if (!/^\d+$/.test(cleanNumber)) {
    return false
  }
  
  // 检查长度（一般为13-19位）
  if (cleanNumber.length < 13 || cleanNumber.length > 19) {
    return false
  }
  
  // Luhn算法验证
  let sum = 0
  let isEven = false
  
  for (let i = cleanNumber.length - 1; i >= 0; i--) {
    let digit = parseInt(cleanNumber.charAt(i), 10)
    
    if (isEven) {
      digit *= 2
      if (digit > 9) {
        digit -= 9
      }
    }
    
    sum += digit
    isEven = !isEven
  }
  
  return sum % 10 === 0
}

/**
 * 验证中文姓名格式
 * @param name 姓名
 * @returns 是否有效
 */
export const isValidChineseName = (name: string): boolean => {
  const chineseNameRegex = /^[\u4e00-\u9fa5]{2,10}$/
  return chineseNameRegex.test(name)
}

/**
 * 验证英文姓名格式
 * @param name 姓名
 * @returns 是否有效
 */
export const isValidEnglishName = (name: string): boolean => {
  const englishNameRegex = /^[a-zA-Z\s]{2,50}$/
  return englishNameRegex.test(name.trim())
}

/**
 * 验证用户名格式
 * @param username 用户名
 * @param options 验证选项
 * @returns 是否有效
 */
export const isValidUsername = (
  username: string,
  options: {
    minLength?: number
    maxLength?: number
    allowNumbers?: boolean
    allowUnderscore?: boolean
    allowHyphen?: boolean
    startWithLetter?: boolean
  } = {}
): boolean => {
  const {
    minLength = 3,
    maxLength = 20,
    allowNumbers = true,
    allowUnderscore = true,
    allowHyphen = false,
    startWithLetter = true
  } = options

  // 长度检查
  if (username.length < minLength || username.length > maxLength) {
    return false
  }

  // 构建正则表达式
  let pattern = '[a-zA-Z]'
  if (!startWithLetter) {
    pattern = '[a-zA-Z'
    if (allowNumbers) pattern += '0-9'
    if (allowUnderscore) pattern += '_'
    if (allowHyphen) pattern += '-'
    pattern += ']'
  }

  let bodyPattern = '[a-zA-Z'
  if (allowNumbers) bodyPattern += '0-9'
  if (allowUnderscore) bodyPattern += '_'
  if (allowHyphen) bodyPattern += '-'
  bodyPattern += ']*'

  const regex = new RegExp(`^${pattern}${bodyPattern}$`)
  return regex.test(username)
}

/**
 * 验证QQ号格式
 * @param qq QQ号
 * @returns 是否有效
 */
export const isValidQQ = (qq: string): boolean => {
  const qqRegex = /^[1-9][0-9]{4,10}$/
  return qqRegex.test(qq)
}

/**
 * 验证微信号格式
 * @param wechat 微信号
 * @returns 是否有效
 */
export const isValidWechat = (wechat: string): boolean => {
  const wechatRegex = /^[a-zA-Z]([a-zA-Z0-9_-]{5,19})+$/
  return wechatRegex.test(wechat)
}

/**
 * 验证车牌号格式（中国大陆）
 * @param plateNumber 车牌号
 * @returns 是否有效
 */
export const isValidPlateNumber = (plateNumber: string): boolean => {
  // 普通车牌
  const normalPlateRegex = /^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4}[A-Z0-9挂学警港澳]$/
  
  // 新能源车牌
  const newEnergyPlateRegex = /^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}$/
  
  return normalPlateRegex.test(plateNumber) || newEnergyPlateRegex.test(plateNumber)
}

/**
 * 验证邮政编码格式（中国大陆）
 * @param zipCode 邮政编码
 * @returns 是否有效
 */
export const isValidZipCode = (zipCode: string): boolean => {
  const zipCodeRegex = /^[1-9]\d{5}$/
  return zipCodeRegex.test(zipCode)
}

/**
 * 验证统一社会信用代码
 * @param creditCode 统一社会信用代码
 * @returns 是否有效
 */
export const isValidCreditCode = (creditCode: string): boolean => {
  const creditCodeRegex = /^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$/
  return creditCodeRegex.test(creditCode)
}

/**
 * 验证护照号格式
 * @param passport 护照号
 * @param country 国家代码
 * @returns 是否有效
 */
export const isValidPassport = (passport: string, country = 'CN'): boolean => {
  switch (country.toUpperCase()) {
    case 'CN': // 中国
      return /^[EeGg]\d{8}$/.test(passport)
    case 'US': // 美国
      return /^\d{9}$/.test(passport)
    case 'UK': // 英国
      return /^\d{9}$/.test(passport)
    default:
      // 通用格式：字母+数字，6-12位
      return /^[A-Za-z0-9]{6,12}$/.test(passport)
  }
}

/**
 * 验证文件扩展名
 * @param filename 文件名
 * @param allowedExtensions 允许的扩展名数组
 * @returns 是否有效
 */
export const isValidFileExtension = (filename: string, allowedExtensions: string[]): boolean => {
  const extension = filename.split('.').pop()?.toLowerCase()
  if (!extension) return false
  
  return allowedExtensions.map(ext => ext.toLowerCase()).includes(extension)
}

/**
 * 验证文件大小
 * @param fileSize 文件大小（字节）
 * @param maxSize 最大大小（字节）
 * @returns 是否有效
 */
export const isValidFileSize = (fileSize: number, maxSize: number): boolean => {
  return fileSize <= maxSize
}

/**
 * 验证日期格式
 * @param dateString 日期字符串
 * @param format 日期格式
 * @returns 是否有效
 */
export const isValidDate = (dateString: string, format = 'YYYY-MM-DD'): boolean => {
  const date = new Date(dateString)
  
  if (isNaN(date.getTime())) {
    return false
  }
  
  // 检查格式
  switch (format) {
    case 'YYYY-MM-DD':
      return /^\d{4}-\d{2}-\d{2}$/.test(dateString)
    case 'YYYY/MM/DD':
      return /^\d{4}\/\d{2}\/\d{2}$/.test(dateString)
    case 'DD/MM/YYYY':
      return /^\d{2}\/\d{2}\/\d{4}$/.test(dateString)
    case 'MM/DD/YYYY':
      return /^\d{2}\/\d{2}\/\d{4}$/.test(dateString)
    default:
      return true
  }
}

/**
 * 验证时间格式
 * @param timeString 时间字符串
 * @param format 时间格式
 * @returns 是否有效
 */
export const isValidTime = (timeString: string, format = 'HH:mm:ss'): boolean => {
  switch (format) {
    case 'HH:mm:ss':
      return /^([01]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$/.test(timeString)
    case 'HH:mm':
      return /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/.test(timeString)
    case 'hh:mm:ss A':
      return /^(0?[1-9]|1[0-2]):[0-5][0-9]:[0-5][0-9] (AM|PM)$/i.test(timeString)
    case 'hh:mm A':
      return /^(0?[1-9]|1[0-2]):[0-5][0-9] (AM|PM)$/i.test(timeString)
    default:
      return true
  }
}

/**
 * 验证颜色值格式
 * @param color 颜色值
 * @param format 颜色格式
 * @returns 是否有效
 */
export const isValidColor = (color: string, format?: 'hex' | 'rgb' | 'rgba' | 'hsl' | 'hsla'): boolean => {
  if (!format) {
    // 自动检测
    return isValidColor(color, 'hex') ||
           isValidColor(color, 'rgb') ||
           isValidColor(color, 'rgba') ||
           isValidColor(color, 'hsl') ||
           isValidColor(color, 'hsla')
  }
  
  switch (format) {
    case 'hex':
      return /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(color)
    case 'rgb':
      return /^rgb\(\s*([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*\)$/.test(color)
    case 'rgba':
      return /^rgba\(\s*([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*((0?\.[0-9]+)|[01])\s*\)$/.test(color)
    case 'hsl':
      return /^hsl\(\s*(0|[1-9]\d?|[12]\d\d|3[0-5]\d|360)\s*,\s*((0|[1-9]\d?|100)%)\s*,\s*((0|[1-9]\d?|100)%)\s*\)$/.test(color)
    case 'hsla':
      return /^hsla\(\s*(0|[1-9]\d?|[12]\d\d|3[0-5]\d|360)\s*,\s*((0|[1-9]\d?|100)%)\s*,\s*((0|[1-9]\d?|100)%)\s*,\s*((0?\.[0-9]+)|[01])\s*\)$/.test(color)
    default:
      return false
  }
}

/**
 * 验证JSON格式
 * @param jsonString JSON字符串
 * @returns 是否有效
 */
export const isValidJSON = (jsonString: string): boolean => {
  try {
    JSON.parse(jsonString)
    return true
  } catch {
    return false
  }
}

/**
 * 验证Base64格式
 * @param base64String Base64字符串
 * @returns 是否有效
 */
export const isValidBase64 = (base64String: string): boolean => {
  const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/
  return base64Regex.test(base64String) && base64String.length % 4 === 0
}

/**
 * 验证正则表达式格式
 * @param regexString 正则表达式字符串
 * @returns 是否有效
 */
export const isValidRegex = (regexString: string): boolean => {
  try {
    new RegExp(regexString)
    return true
  } catch {
    return false
  }
}

/**
 * 自定义验证器类型
 */
export type CustomValidator<T = any> = (value: T) => boolean | string

/**
 * 创建自定义验证器
 * @param validator 验证函数
 * @returns 验证器函数
 */
export const createValidator = <T = any>(validator: CustomValidator<T>) => {
  return validator
}

/**
 * 组合验证器
 * @param validators 验证器数组
 * @returns 组合验证器
 */
export const combineValidators = <T = any>(
  validators: CustomValidator<T>[]
): CustomValidator<T> => {
  return (value: T) => {
    for (const validator of validators) {
      const result = validator(value)
      if (result !== true) {
        return result
      }
    }
    return true
  }
}

/**
 * 异步验证器类型
 */
export type AsyncValidator<T = any> = (value: T) => Promise<boolean | string>

/**
 * 创建异步验证器
 * @param validator 异步验证函数
 * @returns 异步验证器
 */
export const createAsyncValidator = <T = any>(validator: AsyncValidator<T>) => {
  return validator
}

/**
 * 组合异步验证器
 * @param validators 异步验证器数组
 * @returns 组合异步验证器
 */
export const combineAsyncValidators = <T = any>(
  validators: AsyncValidator<T>[]
): AsyncValidator<T> => {
  return async (value: T) => {
    for (const validator of validators) {
      const result = await validator(value)
      if (result !== true) {
        return result
      }
    }
    return true
  }
}