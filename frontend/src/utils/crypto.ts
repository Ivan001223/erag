import CryptoJS from 'crypto-js'

// 默认密钥（实际项目中应该从环境变量获取）
const DEFAULT_SECRET_KEY = 'erag-frontend-secret-key-2024'
const DEFAULT_IV = 'erag-iv-16-bytes'

// 加密配置
interface CryptoConfig {
  secretKey?: string
  iv?: string
  algorithm?: string
}

// 默认配置
const defaultConfig: Required<CryptoConfig> = {
  secretKey: DEFAULT_SECRET_KEY,
  iv: DEFAULT_IV,
  algorithm: 'AES'
}

/**
 * AES加密
 * @param text 要加密的文本
 * @param config 加密配置
 * @returns 加密后的字符串
 */
export const encrypt = (text: string, config?: CryptoConfig): string => {
  try {
    const finalConfig = { ...defaultConfig, ...config }
    
    const key = CryptoJS.enc.Utf8.parse(finalConfig.secretKey)
    const iv = CryptoJS.enc.Utf8.parse(finalConfig.iv)
    
    const encrypted = CryptoJS.AES.encrypt(text, key, {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    })
    
    return encrypted.toString()
  } catch (error) {
    console.error('加密失败:', error)
    return text
  }
}

/**
 * AES解密
 * @param encryptedText 要解密的文本
 * @param config 解密配置
 * @returns 解密后的字符串
 */
export const decrypt = (encryptedText: string, config?: CryptoConfig): string => {
  try {
    const finalConfig = { ...defaultConfig, ...config }
    
    const key = CryptoJS.enc.Utf8.parse(finalConfig.secretKey)
    const iv = CryptoJS.enc.Utf8.parse(finalConfig.iv)
    
    const decrypted = CryptoJS.AES.decrypt(encryptedText, key, {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    })
    
    return decrypted.toString(CryptoJS.enc.Utf8)
  } catch (error) {
    console.error('解密失败:', error)
    return encryptedText
  }
}

/**
 * MD5哈希
 * @param text 要哈希的文本
 * @returns MD5哈希值
 */
export const md5 = (text: string): string => {
  try {
    return CryptoJS.MD5(text).toString()
  } catch (error) {
    console.error('MD5哈希失败:', error)
    return text
  }
}

/**
 * SHA256哈希
 * @param text 要哈希的文本
 * @returns SHA256哈希值
 */
export const sha256 = (text: string): string => {
  try {
    return CryptoJS.SHA256(text).toString()
  } catch (error) {
    console.error('SHA256哈希失败:', error)
    return text
  }
}

/**
 * SHA512哈希
 * @param text 要哈希的文本
 * @returns SHA512哈希值
 */
export const sha512 = (text: string): string => {
  try {
    return CryptoJS.SHA512(text).toString()
  } catch (error) {
    console.error('SHA512哈希失败:', error)
    return text
  }
}

/**
 * Base64编码
 * @param text 要编码的文本
 * @returns Base64编码后的字符串
 */
export const base64Encode = (text: string): string => {
  try {
    return CryptoJS.enc.Base64.stringify(CryptoJS.enc.Utf8.parse(text))
  } catch (error) {
    console.error('Base64编码失败:', error)
    return text
  }
}

/**
 * Base64解码
 * @param encodedText Base64编码的文本
 * @returns 解码后的字符串
 */
export const base64Decode = (encodedText: string): string => {
  try {
    return CryptoJS.enc.Base64.parse(encodedText).toString(CryptoJS.enc.Utf8)
  } catch (error) {
    console.error('Base64解码失败:', error)
    return encodedText
  }
}

/**
 * URL安全的Base64编码
 * @param text 要编码的文本
 * @returns URL安全的Base64编码字符串
 */
export const base64UrlEncode = (text: string): string => {
  try {
    const encoded = base64Encode(text)
    return encoded.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
  } catch (error) {
    console.error('URL安全Base64编码失败:', error)
    return text
  }
}

/**
 * URL安全的Base64解码
 * @param encodedText URL安全的Base64编码文本
 * @returns 解码后的字符串
 */
export const base64UrlDecode = (encodedText: string): string => {
  try {
    let text = encodedText.replace(/-/g, '+').replace(/_/g, '/')
    
    // 补充填充字符
    while (text.length % 4) {
      text += '='
    }
    
    return base64Decode(text)
  } catch (error) {
    console.error('URL安全Base64解码失败:', error)
    return encodedText
  }
}

/**
 * 生成随机字符串
 * @param length 字符串长度
 * @param charset 字符集
 * @returns 随机字符串
 */
export const generateRandomString = (
  length = 32,
  charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
): string => {
  try {
    let result = ''
    for (let i = 0; i < length; i++) {
      result += charset.charAt(Math.floor(Math.random() * charset.length))
    }
    return result
  } catch (error) {
    console.error('生成随机字符串失败:', error)
    return ''
  }
}

/**
 * 生成UUID
 * @returns UUID字符串
 */
export const generateUUID = (): string => {
  try {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  } catch (error) {
    console.error('生成UUID失败:', error)
    return ''
  }
}

/**
 * 生成短ID
 * @param length ID长度
 * @returns 短ID字符串
 */
export const generateShortId = (length = 8): string => {
  try {
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return generateRandomString(length, charset)
  } catch (error) {
    console.error('生成短ID失败:', error)
    return ''
  }
}

/**
 * HMAC-SHA256签名
 * @param message 要签名的消息
 * @param secret 密钥
 * @returns HMAC-SHA256签名
 */
export const hmacSha256 = (message: string, secret: string): string => {
  try {
    return CryptoJS.HmacSHA256(message, secret).toString()
  } catch (error) {
    console.error('HMAC-SHA256签名失败:', error)
    return ''
  }
}

/**
 * 验证HMAC-SHA256签名
 * @param message 原始消息
 * @param signature 签名
 * @param secret 密钥
 * @returns 是否验证通过
 */
export const verifyHmacSha256 = (message: string, signature: string, secret: string): boolean => {
  try {
    const expectedSignature = hmacSha256(message, secret)
    return expectedSignature === signature
  } catch (error) {
    console.error('验证HMAC-SHA256签名失败:', error)
    return false
  }
}

/**
 * 密码强度检测
 * @param password 密码
 * @returns 密码强度等级 (0-4)
 */
export const checkPasswordStrength = (password: string): number => {
  try {
    let strength = 0
    
    // 长度检查
    if (password.length >= 8) strength++
    if (password.length >= 12) strength++
    
    // 字符类型检查
    if (/[a-z]/.test(password)) strength++
    if (/[A-Z]/.test(password)) strength++
    if (/[0-9]/.test(password)) strength++
    if (/[^A-Za-z0-9]/.test(password)) strength++
    
    // 复杂度检查
    if (password.length >= 16 && strength >= 4) strength++
    
    return Math.min(strength, 4)
  } catch (error) {
    console.error('密码强度检测失败:', error)
    return 0
  }
}

/**
 * 生成安全密码
 * @param length 密码长度
 * @param includeSymbols 是否包含特殊字符
 * @returns 安全密码
 */
export const generateSecurePassword = (length = 12, includeSymbols = true): string => {
  try {
    const lowercase = 'abcdefghijklmnopqrstuvwxyz'
    const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    const numbers = '0123456789'
    const symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    let charset = lowercase + uppercase + numbers
    if (includeSymbols) {
      charset += symbols
    }
    
    let password = ''
    
    // 确保至少包含每种字符类型
    password += lowercase.charAt(Math.floor(Math.random() * lowercase.length))
    password += uppercase.charAt(Math.floor(Math.random() * uppercase.length))
    password += numbers.charAt(Math.floor(Math.random() * numbers.length))
    
    if (includeSymbols) {
      password += symbols.charAt(Math.floor(Math.random() * symbols.length))
    }
    
    // 填充剩余长度
    for (let i = password.length; i < length; i++) {
      password += charset.charAt(Math.floor(Math.random() * charset.length))
    }
    
    // 打乱密码字符顺序
    return password.split('').sort(() => Math.random() - 0.5).join('')
  } catch (error) {
    console.error('生成安全密码失败:', error)
    return ''
  }
}

/**
 * 文件哈希计算
 * @param file 文件对象
 * @param algorithm 哈希算法
 * @returns Promise<string> 文件哈希值
 */
export const calculateFileHash = (file: File, algorithm: 'MD5' | 'SHA256' = 'MD5'): Promise<string> => {
  return new Promise((resolve, reject) => {
    try {
      const reader = new FileReader()
      
      reader.onload = (event) => {
        try {
          const arrayBuffer = event.target?.result as ArrayBuffer
          const wordArray = CryptoJS.lib.WordArray.create(arrayBuffer)
          
          let hash: string
          if (algorithm === 'MD5') {
            hash = CryptoJS.MD5(wordArray).toString()
          } else {
            hash = CryptoJS.SHA256(wordArray).toString()
          }
          
          resolve(hash)
        } catch (error) {
          reject(error)
        }
      }
      
      reader.onerror = () => {
        reject(new Error('文件读取失败'))
      }
      
      reader.readAsArrayBuffer(file)
    } catch (error) {
      reject(error)
    }
  })
}

/**
 * 数据完整性验证
 * @param data 数据
 * @param expectedHash 期望的哈希值
 * @param algorithm 哈希算法
 * @returns 是否验证通过
 */
export const verifyDataIntegrity = (
  data: string,
  expectedHash: string,
  algorithm: 'MD5' | 'SHA256' = 'SHA256'
): boolean => {
  try {
    let actualHash: string
    
    if (algorithm === 'MD5') {
      actualHash = md5(data)
    } else {
      actualHash = sha256(data)
    }
    
    return actualHash === expectedHash
  } catch (error) {
    console.error('数据完整性验证失败:', error)
    return false
  }
}

/**
 * 敏感信息脱敏
 * @param text 原始文本
 * @param type 脱敏类型
 * @returns 脱敏后的文本
 */
export const maskSensitiveInfo = (
  text: string,
  type: 'phone' | 'email' | 'idcard' | 'bankcard' | 'custom',
  customPattern?: RegExp,
  replacement = '*'
): string => {
  try {
    if (!text) return text
    
    switch (type) {
      case 'phone':
        return text.replace(/(\d{3})\d{4}(\d{4})/, `$1${replacement.repeat(4)}$2`)
      
      case 'email':
        return text.replace(/(.{1,3}).*(@.*)/, `$1${replacement.repeat(3)}$2`)
      
      case 'idcard':
        return text.replace(/(\d{6})\d{8}(\d{4})/, `$1${replacement.repeat(8)}$2`)
      
      case 'bankcard':
        return text.replace(/(\d{4})\d*(\d{4})/, `$1${replacement.repeat(8)}$2`)
      
      case 'custom':
        if (customPattern) {
          return text.replace(customPattern, replacement.repeat(4))
        }
        return text
      
      default:
        return text
    }
  } catch (error) {
    console.error('敏感信息脱敏失败:', error)
    return text
  }
}