<template>
  <div class="error-page">
    <div class="error-content">
      <!-- 错误图标和数字 -->
      <div class="error-visual">
        <div class="error-number">500</div>
        <div class="error-icon">
          <el-icon><Warning /></el-icon>
        </div>
      </div>
      
      <!-- 错误信息 -->
      <div class="error-info">
        <h1>服务器内部错误</h1>
        <p class="error-description">
          抱歉，服务器遇到了一个意外错误，无法完成您的请求。
        </p>
        <p class="error-suggestion">
          我们的技术团队已经收到错误报告，正在紧急处理中。
        </p>
        
        <!-- 错误详情（开发模式下显示） -->
        <div v-if="showErrorDetails" class="error-details">
          <el-collapse>
            <el-collapse-item title="错误详情" name="details">
              <div class="error-stack">
                <div class="error-item">
                  <span class="label">错误ID：</span>
                  <span class="value">{{ errorId }}</span>
                </div>
                <div class="error-item">
                  <span class="label">时间：</span>
                  <span class="value">{{ errorTime }}</span>
                </div>
                <div class="error-item">
                  <span class="label">请求路径：</span>
                  <span class="value">{{ requestPath }}</span>
                </div>
                <div v-if="errorMessage" class="error-item">
                  <span class="label">错误信息：</span>
                  <span class="value error-message">{{ errorMessage }}</span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      
      <!-- 系统状态 -->
      <div class="system-status">
        <div class="status-header">
          <el-icon><Monitor /></el-icon>
          <span>系统状态检查</span>
        </div>
        <div class="status-grid">
          <div class="status-item">
            <div class="status-label">API 服务</div>
            <div class="status-indicator" :class="apiStatus">
              <el-icon><component :is="getStatusIcon(apiStatus)" /></el-icon>
              <span>{{ getStatusText(apiStatus) }}</span>
            </div>
          </div>
          
          <div class="status-item">
            <div class="status-label">数据库</div>
            <div class="status-indicator" :class="dbStatus">
              <el-icon><component :is="getStatusIcon(dbStatus)" /></el-icon>
              <span>{{ getStatusText(dbStatus) }}</span>
            </div>
          </div>
          
          <div class="status-item">
            <div class="status-label">缓存服务</div>
            <div class="status-indicator" :class="cacheStatus">
              <el-icon><component :is="getStatusIcon(cacheStatus)" /></el-icon>
              <span>{{ getStatusText(cacheStatus) }}</span>
            </div>
          </div>
          
          <div class="status-item">
            <div class="status-label">文件存储</div>
            <div class="status-indicator" :class="storageStatus">
              <el-icon><component :is="getStatusIcon(storageStatus)" /></el-icon>
              <span>{{ getStatusText(storageStatus) }}</span>
            </div>
          </div>
        </div>
        
        <div class="status-actions">
          <el-button size="small" @click="checkSystemStatus" :loading="checking">
            <el-icon><Refresh /></el-icon>
            重新检查
          </el-button>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="error-actions">
        <el-button type="primary" size="large" @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
        
        <el-button size="large" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回上页
        </el-button>
        
        <el-button size="large" @click="refresh">
          <el-icon><Refresh /></el-icon>
          刷新页面
        </el-button>
        
        <el-button size="large" @click="reportError">
          <el-icon><Message /></el-icon>
          报告问题
        </el-button>
      </div>
      
      <!-- 建议操作 -->
      <div class="suggestions">
        <div class="suggestions-title">您可以尝试：</div>
        <ul>
          <li>刷新页面重新尝试</li>
          <li>检查网络连接是否正常</li>
          <li>稍后再试，我们正在修复问题</li>
          <li>如果问题持续存在，请联系技术支持</li>
        </ul>
      </div>
      
      <!-- 联系支持 -->
      <div class="support-section">
        <div class="support-title">需要技术支持？</div>
        <div class="support-info">
          <div class="support-item">
            <el-icon><Message /></el-icon>
            <span>邮箱：support@erag.com</span>
          </div>
          <div class="support-item">
            <el-icon><Phone /></el-icon>
            <span>电话：400-123-4567</span>
          </div>
          <div class="support-item">
            <el-icon><Clock /></el-icon>
            <span>工作时间：周一至周五 9:00-18:00</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 错误报告对话框 -->
    <el-dialog
      v-model="reportDialogVisible"
      title="错误报告"
      width="500px"
      :before-close="handleReportClose"
    >
      <el-form :model="reportForm" label-width="80px">
        <el-form-item label="错误类型">
          <el-select v-model="reportForm.type" placeholder="请选择错误类型">
            <el-option label="页面加载失败" value="page_load" />
            <el-option label="数据获取失败" value="data_fetch" />
            <el-option label="功能异常" value="function_error" />
            <el-option label="性能问题" value="performance" />
            <el-option label="其他问题" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="问题描述">
          <el-input
            v-model="reportForm.description"
            type="textarea"
            :rows="4"
            placeholder="请详细描述您遇到的问题和操作步骤..."
          />
        </el-form-item>
        
        <el-form-item label="联系方式">
          <el-input
            v-model="reportForm.contact"
            placeholder="请输入您的邮箱或电话（可选）"
          />
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="reportForm.includeDetails">
            包含错误详情和系统信息
          </el-checkbox>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="reportDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitReport" :loading="submitting">
            提交报告
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 装饰元素 -->
    <div class="decoration">
      <div class="floating-shape shape-1"></div>
      <div class="floating-shape shape-2"></div>
      <div class="floating-shape shape-3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Warning,
  Monitor,
  HomeFilled,
  ArrowLeft,
  Refresh,
  Message,
  Phone,
  Clock,
  CircleCheck,
  CircleClose,
  Loading
} from '@element-plus/icons-vue'
import { format } from 'date-fns'

const router = useRouter()
const route = useRoute()

// 状态
const checking = ref(false)
const reportDialogVisible = ref(false)
const submitting = ref(false)

// 系统状态
const apiStatus = ref('error')
const dbStatus = ref('error')
const cacheStatus = ref('warning')
const storageStatus = ref('normal')

// 错误信息
const errorId = ref(generateErrorId())
const errorTime = ref(format(new Date(), 'yyyy-MM-dd HH:mm:ss'))
const requestPath = ref(route.fullPath)
const errorMessage = ref('')

// 错误报告表单
const reportForm = reactive({
  type: '',
  description: '',
  contact: '',
  includeDetails: true
})

// 是否显示错误详情（开发模式）
const showErrorDetails = computed(() => {
  return import.meta.env.DEV || route.query.debug === 'true'
})

// 生成错误ID
function generateErrorId() {
  return 'ERR-' + Date.now().toString(36).toUpperCase() + '-' + Math.random().toString(36).substr(2, 5).toUpperCase()
}

// 获取状态图标
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'normal':
      return 'CircleCheck'
    case 'warning':
      return 'Loading'
    case 'error':
      return 'CircleClose'
    default:
      return 'Loading'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'normal':
      return '正常'
    case 'warning':
      return '异常'
    case 'error':
      return '错误'
    default:
      return '检查中'
  }
}

// 检查系统状态
const checkSystemStatus = async () => {
  checking.value = true
  
  try {
    // 重置状态
    apiStatus.value = 'checking'
    dbStatus.value = 'checking'
    cacheStatus.value = 'checking'
    storageStatus.value = 'checking'
    
    // 模拟检查各个服务状态
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 这里应该调用实际的健康检查 API
    // const healthCheck = await api.checkHealth()
    
    // 模拟结果
    apiStatus.value = Math.random() > 0.5 ? 'normal' : 'error'
    dbStatus.value = Math.random() > 0.3 ? 'normal' : 'error'
    cacheStatus.value = Math.random() > 0.7 ? 'normal' : 'warning'
    storageStatus.value = 'normal'
    
    ElMessage.success('系统状态检查完成')
    
  } catch (error) {
    ElMessage.error('状态检查失败')
  } finally {
    checking.value = false
  }
}

// 返回首页
const goHome = () => {
  router.push('/dashboard')
}

// 返回上一页
const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    goHome()
  }
}

// 刷新页面
const refresh = () => {
  window.location.reload()
}

// 报告错误
const reportError = () => {
  reportDialogVisible.value = true
}

// 关闭报告对话框
const handleReportClose = () => {
  reportForm.type = ''
  reportForm.description = ''
  reportForm.contact = ''
  reportForm.includeDetails = true
  reportDialogVisible.value = false
}

// 提交错误报告
const submitReport = async () => {
  if (!reportForm.type) {
    ElMessage.warning('请选择错误类型')
    return
  }
  
  if (!reportForm.description.trim()) {
    ElMessage.warning('请描述您遇到的问题')
    return
  }
  
  try {
    submitting.value = true
    
    const reportData = {
      ...reportForm,
      errorId: errorId.value,
      errorTime: errorTime.value,
      requestPath: requestPath.value,
      userAgent: navigator.userAgent,
      url: window.location.href
    }
    
    if (reportForm.includeDetails) {
      reportData.systemStatus = {
        api: apiStatus.value,
        database: dbStatus.value,
        cache: cacheStatus.value,
        storage: storageStatus.value
      }
    }
    
    // 这里应该调用提交错误报告的 API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('错误报告已提交，感谢您的反馈！')
    handleReportClose()
    
  } catch (error) {
    ElMessage.error('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

// 页面初始化
onMounted(() => {
  // 获取错误信息
  const error = route.query.error as string
  if (error) {
    try {
      const errorInfo = JSON.parse(decodeURIComponent(error))
      errorMessage.value = errorInfo.message || ''
    } catch (e) {
      errorMessage.value = error
    }
  }
  
  // 自动检查系统状态
  checkSystemStatus()
  
  // 记录错误日志
  console.error('500 Error:', {
    errorId: errorId.value,
    time: errorTime.value,
    path: requestPath.value,
    message: errorMessage.value
  })
})
</script>

<style lang="scss" scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.error-content {
  max-width: 800px;
  width: 100%;
  text-align: center;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 48px 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 1;
}

.error-visual {
  position: relative;
  margin-bottom: 32px;
  
  .error-number {
    font-size: 120px;
    font-weight: 900;
    color: #ff6b6b;
    line-height: 1;
    margin-bottom: 16px;
    text-shadow: 0 4px 8px rgba(255, 107, 107, 0.3);
    
    @media (max-width: 480px) {
      font-size: 80px;
    }
  }
  
  .error-icon {
    .el-icon {
      font-size: 64px;
      color: #f56565;
      
      @media (max-width: 480px) {
        font-size: 48px;
      }
    }
  }
}

.error-info {
  margin-bottom: 32px;
  
  h1 {
    font-size: 32px;
    font-weight: 700;
    color: #2d3748;
    margin: 0 0 16px 0;
    
    @media (max-width: 480px) {
      font-size: 24px;
    }
  }
  
  .error-description {
    font-size: 18px;
    color: #4a5568;
    margin: 0 0 16px 0;
    line-height: 1.6;
    
    @media (max-width: 480px) {
      font-size: 16px;
    }
  }
  
  .error-suggestion {
    font-size: 16px;
    color: #718096;
    margin: 0 0 24px 0;
    
    @media (max-width: 480px) {
      font-size: 14px;
    }
  }
}

.error-details {
  margin-top: 24px;
  text-align: left;
  
  .error-stack {
    .error-item {
      display: flex;
      margin-bottom: 8px;
      
      .label {
        min-width: 80px;
        color: #718096;
        font-size: 14px;
      }
      
      .value {
        color: #2d3748;
        font-size: 14px;
        word-break: break-all;
        
        &.error-message {
          color: #e53e3e;
          font-family: monospace;
        }
      }
    }
  }
}

.system-status {
  margin-bottom: 32px;
  padding: 24px;
  background: #f7fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  
  .status-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 20px;
    font-weight: 600;
    color: #2d3748;
    
    .el-icon {
      font-size: 20px;
      color: #4299e1;
    }
  }
  
  .status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
    
    @media (max-width: 480px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  .status-item {
    text-align: center;
    
    .status-label {
      font-size: 12px;
      color: #718096;
      margin-bottom: 8px;
    }
    
    .status-indicator {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 8px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
      
      &.normal {
        background: #c6f6d5;
        color: #22543d;
      }
      
      &.warning {
        background: #fef5e7;
        color: #c05621;
      }
      
      &.error {
        background: #fed7d7;
        color: #c53030;
      }
      
      &.checking {
        background: #e6fffa;
        color: #234e52;
      }
      
      .el-icon {
        font-size: 14px;
      }
    }
  }
  
  .status-actions {
    text-align: center;
  }
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 32px;
  
  .el-button {
    min-width: 120px;
    
    @media (max-width: 480px) {
      min-width: 100px;
      flex: 1;
    }
  }
}

.suggestions {
  margin-bottom: 32px;
  text-align: left;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
  
  .suggestions-title {
    font-size: 16px;
    color: #4a5568;
    margin-bottom: 12px;
    text-align: center;
  }
  
  ul {
    margin: 0;
    padding-left: 20px;
    
    li {
      color: #718096;
      font-size: 14px;
      line-height: 1.8;
      margin-bottom: 4px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

.support-section {
  padding: 20px;
  background: #f7fafc;
  border-radius: 12px;
  border-left: 4px solid #4299e1;
  
  .support-title {
    font-size: 16px;
    color: #2d3748;
    font-weight: 600;
    margin-bottom: 16px;
    text-align: center;
  }
  
  .support-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
    
    @media (min-width: 768px) {
      flex-direction: row;
      justify-content: space-around;
    }
  }
  
  .support-item {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #4a5568;
    font-size: 14px;
    
    .el-icon {
      color: #4299e1;
      font-size: 16px;
    }
  }
}

.decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
}

.floating-shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float 6s ease-in-out infinite;
  
  &.shape-1 {
    width: 80px;
    height: 80px;
    top: 15%;
    left: 10%;
    animation-delay: 0s;
  }
  
  &.shape-2 {
    width: 120px;
    height: 120px;
    top: 25%;
    right: 15%;
    animation-delay: 2s;
  }
  
  &.shape-3 {
    width: 60px;
    height: 60px;
    bottom: 20%;
    left: 20%;
    animation-delay: 4s;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .error-content {
    padding: 32px 24px;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 100%;
      max-width: 200px;
    }
  }
  
  .system-status {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .error-page {
    padding: 16px;
  }
  
  .error-content {
    padding: 24px 16px;
  }
  
  .suggestions {
    text-align: center;
    
    ul {
      text-align: left;
      padding-left: 16px;
    }
  }
  
  .support-section {
    padding: 16px;
    
    .support-info {
      align-items: flex-start;
    }
  }
}
</style>