<template>
  <div class="error-page">
    <div class="error-container">
      <div class="error-content">
        <!-- 错误图标 -->
        <div class="error-icon">
          <svg viewBox="0 0 1024 1024" width="200" height="200">
            <path
              d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"
              fill="#f5222d"
            />
            <path
              d="M464 688a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm24-112h48c4.4 0 8-3.6 8-8V296c0-4.4-3.6-8-8-8h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8z"
              fill="#f5222d"
            />
          </svg>
        </div>
        
        <!-- 错误信息 -->
        <div class="error-info">
          <h1 class="error-title">500</h1>
          <h2 class="error-subtitle">服务器内部错误</h2>
          <p class="error-description">
            抱歉，服务器遇到了一个内部错误，无法完成您的请求。我们的技术团队已经收到通知，正在紧急处理中。
          </p>
        </div>
        
        <!-- 错误详情 -->
        <div class="error-details" v-if="showDetails">
          <div class="details-header">
            <h3>错误详情</h3>
            <el-button size="small" @click="copyErrorInfo">
              <el-icon><CopyDocument /></el-icon>
              复制错误信息
            </el-button>
          </div>
          <div class="details-content">
            <div class="detail-item">
              <span class="detail-label">错误ID:</span>
              <span class="detail-value">{{ errorInfo.id }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">时间:</span>
              <span class="detail-value">{{ errorInfo.timestamp }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">请求路径:</span>
              <span class="detail-value">{{ errorInfo.path }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">用户代理:</span>
              <span class="detail-value">{{ errorInfo.userAgent }}</span>
            </div>
          </div>
        </div>
        
        <!-- 操作按钮 -->
        <div class="error-actions">
          <el-button type="primary" size="large" @click="refreshPage">
            <el-icon><Refresh /></el-icon>
            刷新页面
          </el-button>
          <el-button size="large" @click="goHome">
            <el-icon><House /></el-icon>
            返回首页
          </el-button>
          <el-button size="large" @click="reportError">
            <el-icon><Warning /></el-icon>
            报告问题
          </el-button>
        </div>
        
        <!-- 切换详情显示 -->
        <div class="error-toggle">
          <el-button text @click="toggleDetails">
            <el-icon><InfoFilled /></el-icon>
            {{ showDetails ? '隐藏' : '显示' }}错误详情
          </el-button>
        </div>
        
        <!-- 建议操作 -->
        <div class="error-suggestions">
          <h3>解决建议：</h3>
          <ul>
            <li>刷新页面重试</li>
            <li>检查网络连接是否正常</li>
            <li>稍后再试，服务器可能正在维护</li>
            <li>如果问题持续存在，请联系技术支持</li>
          </ul>
        </div>
        
        <!-- 联系信息 -->
        <div class="error-contact">
          <h3>需要帮助？</h3>
          <div class="contact-methods">
            <div class="contact-item">
              <el-icon><Message /></el-icon>
              <span>邮箱：support@company.com</span>
            </div>
            <div class="contact-item">
              <el-icon><Phone /></el-icon>
              <span>电话：400-123-4567</span>
            </div>
            <div class="contact-item">
              <el-icon><ChatDotRound /></el-icon>
              <span>在线客服：工作日 9:00-18:00</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 装饰元素 -->
      <div class="error-decoration">
        <div class="decoration-gear gear-1">
          <svg viewBox="0 0 24 24" width="60" height="60">
            <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.68 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" fill="rgba(245, 34, 45, 0.3)"/>
          </svg>
        </div>
        <div class="decoration-gear gear-2">
          <svg viewBox="0 0 24 24" width="40" height="40">
            <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.68 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" fill="rgba(245, 34, 45, 0.2)"/>
          </svg>
        </div>
        <div class="decoration-gear gear-3">
          <svg viewBox="0 0 24 24" width="80" height="80">
            <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.68 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" fill="rgba(245, 34, 45, 0.1)"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh,
  House,
  Warning,
  InfoFilled,
  CopyDocument,
  Message,
  Phone,
  ChatDotRound
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const showDetails = ref(false)

// 错误信息
const errorInfo = reactive({
  id: '',
  timestamp: '',
  path: '',
  userAgent: ''
})

// 生成错误ID
const generateErrorId = () => {
  return 'ERR-' + Date.now().toString(36).toUpperCase() + '-' + Math.random().toString(36).substr(2, 5).toUpperCase()
}

// 刷新页面
const refreshPage = () => {
  window.location.reload()
}

// 返回首页
const goHome = () => {
  router.push('/')
}

// 报告错误
const reportError = async () => {
  try {
    await ElMessageBox.prompt(
      '请描述您遇到的问题，我们会尽快处理：',
      '报告问题',
      {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '请详细描述问题...',
        inputValidator: (value: string) => {
          if (!value || value.trim().length < 10) {
            return '问题描述至少需要10个字符'
          }
          return true
        }
      }
    )
    
    ElMessage.success('问题报告已提交，我们会尽快处理')
  } catch {
    // 用户取消
  }
}

// 切换详情显示
const toggleDetails = () => {
  showDetails.value = !showDetails.value
}

// 复制错误信息
const copyErrorInfo = async () => {
  const errorText = `错误ID: ${errorInfo.id}\n时间: ${errorInfo.timestamp}\n请求路径: ${errorInfo.path}\n用户代理: ${errorInfo.userAgent}`
  
  try {
    await navigator.clipboard.writeText(errorText)
    ElMessage.success('错误信息已复制到剪贴板')
  } catch {
    // 降级方案
    const textArea = document.createElement('textarea')
    textArea.value = errorText
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    ElMessage.success('错误信息已复制到剪贴板')
  }
}

// 初始化错误信息
const initErrorInfo = () => {
  errorInfo.id = generateErrorId()
  errorInfo.timestamp = new Date().toLocaleString('zh-CN')
  errorInfo.path = route.fullPath
  errorInfo.userAgent = navigator.userAgent
}

onMounted(() => {
  initErrorInfo()
})
</script>

<style scoped lang="scss">
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.error-container {
  max-width: 900px;
  width: 100%;
  position: relative;
  z-index: 2;
}

.error-content {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 60px 40px;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.error-icon {
  margin-bottom: 30px;
  
  svg {
    filter: drop-shadow(0 10px 20px rgba(245, 34, 45, 0.3));
    animation: shake 1s ease-in-out infinite;
  }
}

@keyframes shake {
  0%, 100% {
    transform: translateX(0);
  }
  10%, 30%, 50%, 70%, 90% {
    transform: translateX(-2px);
  }
  20%, 40%, 60%, 80% {
    transform: translateX(2px);
  }
}

.error-info {
  margin-bottom: 40px;
  
  .error-title {
    font-size: 72px;
    font-weight: 700;
    color: #f5222d;
    margin: 0 0 10px 0;
    text-shadow: 0 4px 8px rgba(245, 34, 45, 0.3);
    animation: flicker 2s ease-in-out infinite;
  }
  
  .error-subtitle {
    font-size: 32px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 20px 0;
  }
  
  .error-description {
    font-size: 16px;
    color: #606266;
    line-height: 1.6;
    margin: 0;
    max-width: 600px;
    margin: 0 auto;
  }
}

@keyframes flicker {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.error-details {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 30px;
  text-align: left;
  
  .details-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    
    h3 {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }
  }
  
  .details-content {
    .detail-item {
      display: flex;
      margin-bottom: 10px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .detail-label {
        font-weight: 500;
        color: #606266;
        min-width: 80px;
        margin-right: 10px;
      }
      
      .detail-value {
        color: #303133;
        word-break: break-all;
        flex: 1;
      }
    }
  }
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-bottom: 30px;
  flex-wrap: wrap;
  
  .el-button {
    min-width: 140px;
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

.error-toggle {
  margin-bottom: 30px;
  
  .el-button {
    color: #606266;
    
    &:hover {
      color: #409eff;
    }
  }
}

.error-suggestions {
  text-align: left;
  max-width: 500px;
  margin: 0 auto 30px;
  padding: 20px;
  background: rgba(245, 34, 45, 0.1);
  border-radius: 12px;
  border-left: 4px solid #f5222d;
  
  h3 {
    margin: 0 0 15px 0;
    color: #303133;
    font-size: 16px;
    font-weight: 600;
  }
  
  ul {
    margin: 0;
    padding-left: 20px;
    
    li {
      color: #606266;
      line-height: 1.6;
      margin-bottom: 8px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

.error-contact {
  text-align: center;
  
  h3 {
    margin: 0 0 20px 0;
    color: #303133;
    font-size: 16px;
    font-weight: 600;
  }
  
  .contact-methods {
    display: flex;
    justify-content: center;
    gap: 30px;
    flex-wrap: wrap;
    
    .contact-item {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #606266;
      font-size: 14px;
      
      .el-icon {
        color: #409eff;
      }
    }
  }
}

.error-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.decoration-gear {
  position: absolute;
  animation: rotate-gear 10s linear infinite;
  
  &.gear-1 {
    top: 15%;
    left: 10%;
    animation-direction: normal;
  }
  
  &.gear-2 {
    top: 60%;
    right: 15%;
    animation-direction: reverse;
    animation-duration: 8s;
  }
  
  &.gear-3 {
    bottom: 20%;
    left: 20%;
    animation-direction: normal;
    animation-duration: 12s;
  }
}

@keyframes rotate-gear {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .error-content {
    padding: 40px 20px;
  }
  
  .error-icon svg {
    width: 150px;
    height: 150px;
  }
  
  .error-info {
    .error-title {
      font-size: 48px;
    }
    
    .error-subtitle {
      font-size: 24px;
    }
    
    .error-description {
      font-size: 14px;
    }
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 100%;
      max-width: 280px;
    }
  }
  
  .contact-methods {
    flex-direction: column;
    gap: 15px;
  }
  
  .details-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
}

@media (max-width: 480px) {
  .error-page {
    padding: 10px;
  }
  
  .error-content {
    padding: 30px 15px;
  }
  
  .error-icon svg {
    width: 120px;
    height: 120px;
  }
  
  .error-info {
    .error-title {
      font-size: 36px;
    }
    
    .error-subtitle {
      font-size: 20px;
    }
  }
  
  .error-suggestions {
    text-align: center;
    
    ul {
      text-align: left;
    }
  }
}
</style>