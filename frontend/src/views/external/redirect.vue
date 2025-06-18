<template>
  <div class="redirect-page">
    <div class="redirect-container">
      <div class="redirect-content">
        <!-- 加载动画 -->
        <div class="loading-animation">
          <div class="spinner">
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
          </div>
        </div>
        
        <!-- 重定向信息 -->
        <div class="redirect-info">
          <h2 class="redirect-title">正在跳转...</h2>
          <p class="redirect-description">
            {{ redirectMessage }}
          </p>
          
          <!-- 目标URL显示 -->
          <div class="redirect-url" v-if="targetUrl && showUrl">
            <span class="url-label">目标地址：</span>
            <span class="url-value">{{ displayUrl }}</span>
          </div>
          
          <!-- 倒计时 -->
          <div class="redirect-countdown" v-if="countdown > 0">
            <span>{{ countdown }} 秒后自动跳转</span>
          </div>
          
          <!-- 手动跳转按钮 -->
          <div class="redirect-actions">
            <el-button 
              type="primary" 
              size="large" 
              @click="handleRedirect"
              :loading="isRedirecting"
            >
              <el-icon><Right /></el-icon>
              立即跳转
            </el-button>
            
            <el-button 
              size="large" 
              @click="cancelRedirect"
              :disabled="isRedirecting"
            >
              <el-icon><Close /></el-icon>
              取消跳转
            </el-button>
          </div>
        </div>
        
        <!-- 安全提示 -->
        <div class="security-notice" v-if="isExternalUrl">
          <div class="notice-header">
            <el-icon class="warning-icon"><Warning /></el-icon>
            <span>安全提示</span>
          </div>
          <p class="notice-content">
            您即将离开当前网站，跳转到外部链接。请确认目标网站的安全性。
          </p>
        </div>
        
        <!-- 错误信息 -->
        <div class="redirect-error" v-if="error">
          <el-alert
            :title="error"
            type="error"
            :closable="false"
            show-icon
          />
          <div class="error-actions">
            <el-button @click="goBack">
              <el-icon><ArrowLeft /></el-icon>
              返回上页
            </el-button>
            <el-button @click="goHome">
              <el-icon><House /></el-icon>
              返回首页
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Right,
  Close,
  Warning,
  ArrowLeft,
  House
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

// 响应式数据
const targetUrl = ref('')
const countdown = ref(5)
const isRedirecting = ref(false)
const error = ref('')
const showUrl = ref(true)
const autoRedirect = ref(true)

let countdownTimer: NodeJS.Timeout | null = null

// 计算属性
const redirectMessage = computed(() => {
  if (error.value) {
    return '跳转失败'
  }
  if (isRedirecting.value) {
    return '正在跳转，请稍候...'
  }
  return '页面即将跳转到目标地址'
})

const displayUrl = computed(() => {
  if (!targetUrl.value) return ''
  
  // 如果URL太长，截断显示
  if (targetUrl.value.length > 60) {
    return targetUrl.value.substring(0, 57) + '...'
  }
  return targetUrl.value
})

const isExternalUrl = computed(() => {
  if (!targetUrl.value) return false
  
  try {
    const url = new URL(targetUrl.value)
    const currentHost = window.location.host
    return url.host !== currentHost
  } catch {
    return false
  }
})

// 验证URL
const validateUrl = (url: string): boolean => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

// 检查URL安全性
const isUrlSafe = (url: string): boolean => {
  const dangerousProtocols = ['javascript:', 'data:', 'vbscript:']
  const lowerUrl = url.toLowerCase()
  
  return !dangerousProtocols.some(protocol => lowerUrl.startsWith(protocol))
}

// 执行重定向
const handleRedirect = async () => {
  if (!targetUrl.value) {
    error.value = '缺少目标地址参数'
    return
  }
  
  if (!validateUrl(targetUrl.value)) {
    error.value = '目标地址格式不正确'
    return
  }
  
  if (!isUrlSafe(targetUrl.value)) {
    error.value = '目标地址存在安全风险'
    return
  }
  
  isRedirecting.value = true
  
  try {
    // 清除倒计时
    if (countdownTimer) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
    
    // 延迟一下，让用户看到加载状态
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 执行跳转
    if (isExternalUrl.value) {
      // 外部链接在新窗口打开
      window.open(targetUrl.value, '_blank', 'noopener,noreferrer')
      // 返回上一页或首页
      if (window.history.length > 1) {
        router.go(-1)
      } else {
        router.push('/')
      }
    } else {
      // 内部链接直接跳转
      window.location.href = targetUrl.value
    }
  } catch (err) {
    console.error('Redirect error:', err)
    error.value = '跳转失败，请稍后重试'
    isRedirecting.value = false
  }
}

// 取消重定向
const cancelRedirect = () => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  
  countdown.value = 0
  autoRedirect.value = false
  
  ElMessage.info('已取消自动跳转')
}

// 返回上页
const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}

// 返回首页
const goHome = () => {
  router.push('/')
}

// 开始倒计时
const startCountdown = () => {
  if (!autoRedirect.value) return
  
  countdownTimer = setInterval(() => {
    countdown.value--
    
    if (countdown.value <= 0) {
      if (countdownTimer) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
      handleRedirect()
    }
  }, 1000)
}

// 初始化
const init = () => {
  // 从查询参数获取目标URL
  const url = route.query.url as string
  const redirect = route.query.redirect as string
  const target = route.query.target as string
  
  // 支持多种参数名
  targetUrl.value = url || redirect || target || ''
  
  // 从查询参数获取其他配置
  const autoParam = route.query.auto as string
  const showUrlParam = route.query.showUrl as string
  const delayParam = route.query.delay as string
  
  if (autoParam === 'false') {
    autoRedirect.value = false
  }
  
  if (showUrlParam === 'false') {
    showUrl.value = false
  }
  
  if (delayParam && !isNaN(Number(delayParam))) {
    countdown.value = Math.max(1, Math.min(30, Number(delayParam)))
  }
  
  // 验证目标URL
  if (!targetUrl.value) {
    error.value = '缺少目标地址参数'
    return
  }
  
  if (!validateUrl(targetUrl.value)) {
    error.value = '目标地址格式不正确'
    return
  }
  
  if (!isUrlSafe(targetUrl.value)) {
    error.value = '目标地址存在安全风险'
    return
  }
  
  // 开始倒计时
  if (autoRedirect.value) {
    startCountdown()
  }
}

onMounted(() => {
  init()
})

onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
})
</script>

<style scoped lang="scss">
.redirect-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.redirect-container {
  max-width: 600px;
  width: 100%;
}

.redirect-content {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.loading-animation {
  margin-bottom: 30px;
  
  .spinner {
    position: relative;
    width: 80px;
    height: 80px;
    margin: 0 auto;
    
    .spinner-ring {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      border: 3px solid transparent;
      border-top: 3px solid #667eea;
      border-radius: 50%;
      animation: spin 1.2s linear infinite;
      
      &:nth-child(2) {
        animation-delay: -0.4s;
        border-top-color: #764ba2;
      }
      
      &:nth-child(3) {
        animation-delay: -0.8s;
        border-top-color: #f093fb;
      }
    }
  }
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.redirect-info {
  margin-bottom: 30px;
  
  .redirect-title {
    font-size: 28px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 15px 0;
  }
  
  .redirect-description {
    font-size: 16px;
    color: #606266;
    line-height: 1.6;
    margin: 0 0 20px 0;
  }
}

.redirect-url {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  text-align: left;
  
  .url-label {
    font-weight: 500;
    color: #606266;
    display: block;
    margin-bottom: 5px;
  }
  
  .url-value {
    color: #303133;
    word-break: break-all;
    font-family: 'Courier New', monospace;
    font-size: 14px;
  }
}

.redirect-countdown {
  font-size: 18px;
  font-weight: 500;
  color: #667eea;
  margin-bottom: 25px;
  
  span {
    background: rgba(102, 126, 234, 0.1);
    padding: 8px 16px;
    border-radius: 20px;
    border: 1px solid rgba(102, 126, 234, 0.2);
  }
}

.redirect-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  flex-wrap: wrap;
  
  .el-button {
    min-width: 120px;
    height: 44px;
    border-radius: 22px;
    font-weight: 500;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
    }
  }
}

.security-notice {
  background: rgba(255, 193, 7, 0.1);
  border: 1px solid rgba(255, 193, 7, 0.3);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  
  .notice-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 10px;
    
    .warning-icon {
      color: #faad14;
      font-size: 18px;
    }
    
    span {
      font-weight: 600;
      color: #303133;
    }
  }
  
  .notice-content {
    color: #606266;
    line-height: 1.6;
    margin: 0;
    text-align: center;
  }
}

.redirect-error {
  .el-alert {
    margin-bottom: 20px;
  }
  
  .error-actions {
    display: flex;
    justify-content: center;
    gap: 15px;
    flex-wrap: wrap;
    
    .el-button {
      min-width: 120px;
      height: 40px;
      border-radius: 20px;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .redirect-content {
    padding: 30px 20px;
  }
  
  .loading-animation .spinner {
    width: 60px;
    height: 60px;
  }
  
  .redirect-info .redirect-title {
    font-size: 24px;
  }
  
  .redirect-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 100%;
      max-width: 280px;
    }
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 100%;
      max-width: 200px;
    }
  }
}

@media (max-width: 480px) {
  .redirect-page {
    padding: 10px;
  }
  
  .redirect-content {
    padding: 25px 15px;
  }
  
  .redirect-info .redirect-title {
    font-size: 20px;
  }
  
  .redirect-countdown {
    font-size: 16px;
  }
}
</style>