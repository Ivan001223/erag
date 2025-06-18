<template>
  <div class="error-page">
    <div class="error-content">
      <!-- 错误图标和数字 -->
      <div class="error-visual">
        <div class="error-number">403</div>
        <div class="error-icon">
          <el-icon><Lock /></el-icon>
        </div>
      </div>
      
      <!-- 错误信息 -->
      <div class="error-info">
        <h1>访问被拒绝</h1>
        <p class="error-description">
          抱歉，您没有权限访问此页面或资源。
        </p>
        <p class="error-suggestion">
          可能的原因和解决方案：
        </p>
        
        <!-- 建议操作 -->
        <div class="suggestions">
          <ul>
            <li>您的账户权限不足，请联系管理员</li>
            <li>登录状态已过期，请重新登录</li>
            <li>访问的资源需要特殊权限</li>
            <li>系统正在维护中，请稍后再试</li>
          </ul>
        </div>
      </div>
      
      <!-- 权限信息 -->
      <div v-if="userInfo" class="permission-info">
        <div class="info-card">
          <div class="info-header">
            <el-icon><User /></el-icon>
            <span>当前用户信息</span>
          </div>
          <div class="info-content">
            <div class="info-item">
              <span class="label">用户名：</span>
              <span class="value">{{ userInfo.username }}</span>
            </div>
            <div class="info-item">
              <span class="label">角色：</span>
              <span class="value">{{ userInfo.role }}</span>
            </div>
            <div class="info-item">
              <span class="label">权限级别：</span>
              <span class="value">{{ userInfo.permissionLevel }}</span>
            </div>
          </div>
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
        
        <el-button size="large" @click="reLogin">
          <el-icon><Refresh /></el-icon>
          重新登录
        </el-button>
      </div>
      
      <!-- 联系管理员 -->
      <div class="contact-section">
        <div class="contact-title">需要帮助？</div>
        <div class="contact-actions">
          <el-button type="info" plain @click="showContactDialog">
            <el-icon><Message /></el-icon>
            联系管理员
          </el-button>
          
          <el-button type="info" plain @click="showHelpDialog">
            <el-icon><QuestionFilled /></el-icon>
            查看帮助
          </el-button>
        </div>
      </div>
      
      <!-- 可访问的页面 -->
      <div class="accessible-pages">
        <div class="pages-title">您可以访问的页面：</div>
        <div class="pages-grid">
          <router-link 
            v-for="page in accessiblePages" 
            :key="page.path"
            :to="page.path" 
            class="page-link"
          >
            <el-icon><component :is="page.icon" /></el-icon>
            <span>{{ page.name }}</span>
          </router-link>
        </div>
      </div>
    </div>
    
    <!-- 联系管理员对话框 -->
    <el-dialog
      v-model="contactDialogVisible"
      title="联系管理员"
      width="500px"
      :before-close="handleContactClose"
    >
      <el-form :model="contactForm" label-width="80px">
        <el-form-item label="问题类型">
          <el-select v-model="contactForm.type" placeholder="请选择问题类型">
            <el-option label="权限申请" value="permission" />
            <el-option label="账户问题" value="account" />
            <el-option label="系统故障" value="system" />
            <el-option label="其他问题" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="问题描述">
          <el-input
            v-model="contactForm.description"
            type="textarea"
            :rows="4"
            placeholder="请详细描述您遇到的问题..."
          />
        </el-form-item>
        
        <el-form-item label="联系方式">
          <el-input
            v-model="contactForm.contact"
            placeholder="请输入您的邮箱或电话"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="contactDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitContact" :loading="submitting">
            提交
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 帮助对话框 -->
    <el-dialog
      v-model="helpDialogVisible"
      title="权限说明"
      width="600px"
    >
      <div class="help-content">
        <h4>权限级别说明：</h4>
        <ul>
          <li><strong>管理员：</strong>拥有系统所有权限，可以管理用户和系统设置</li>
          <li><strong>编辑者：</strong>可以创建、编辑和删除知识图谱内容</li>
          <li><strong>查看者：</strong>只能查看知识图谱内容，无法进行编辑</li>
          <li><strong>访客：</strong>仅能访问公开内容</li>
        </ul>
        
        <h4>如何申请权限：</h4>
        <ol>
          <li>点击"联系管理员"按钮</li>
          <li>选择"权限申请"类型</li>
          <li>详细说明您需要的权限和用途</li>
          <li>提供您的联系方式</li>
          <li>等待管理员审核和回复</li>
        </ol>
        
        <h4>常见问题：</h4>
        <ul>
          <li><strong>Q：为什么我无法访问某些页面？</strong><br>
              A：可能是您的权限级别不够，或者登录状态已过期。</li>
          <li><strong>Q：如何提升我的权限级别？</strong><br>
              A：请联系系统管理员申请权限提升。</li>
          <li><strong>Q：权限申请需要多长时间？</strong><br>
              A：通常在1-3个工作日内处理完成。</li>
        </ul>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button type="primary" @click="helpDialogVisible = false">我知道了</el-button>
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Lock,
  User,
  HomeFilled,
  ArrowLeft,
  Refresh,
  Message,
  QuestionFilled,
  DataBoard,
  Document,
  Setting
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 对话框状态
const contactDialogVisible = ref(false)
const helpDialogVisible = ref(false)
const submitting = ref(false)

// 联系表单
const contactForm = reactive({
  type: '',
  description: '',
  contact: ''
})

// 用户信息
const userInfo = computed(() => {
  const user = userStore.userInfo
  if (!user) return null
  
  return {
    username: user.username || '未知用户',
    role: user.role || '未知角色',
    permissionLevel: getRoleDisplayName(user.role)
  }
})

// 可访问的页面（根据用户权限动态生成）
const accessiblePages = computed(() => {
  const pages = []
  
  // 所有用户都可以访问的页面
  pages.push({
    name: '仪表盘',
    path: '/dashboard',
    icon: 'DataBoard'
  })
  
  // 根据用户权限添加其他页面
  if (userStore.hasPermission('view:knowledge')) {
    pages.push({
      name: '知识图谱',
      path: '/knowledge/graphs',
      icon: 'Document'
    })
  }
  
  if (userStore.hasPermission('admin')) {
    pages.push({
      name: '系统设置',
      path: '/system/settings',
      icon: 'Setting'
    })
  }
  
  return pages
})

// 获取角色显示名称
const getRoleDisplayName = (role: string) => {
  const roleMap: Record<string, string> = {
    admin: '管理员',
    editor: '编辑者',
    viewer: '查看者',
    guest: '访客'
  }
  return roleMap[role] || '未知'
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

// 重新登录
const reLogin = () => {
  userStore.logout()
  router.push('/login?redirect=' + encodeURIComponent(router.currentRoute.value.fullPath))
}

// 显示联系对话框
const showContactDialog = () => {
  contactDialogVisible.value = true
}

// 显示帮助对话框
const showHelpDialog = () => {
  helpDialogVisible.value = true
}

// 关闭联系对话框
const handleContactClose = () => {
  contactForm.type = ''
  contactForm.description = ''
  contactForm.contact = ''
  contactDialogVisible.value = false
}

// 提交联系表单
const submitContact = async () => {
  if (!contactForm.type) {
    ElMessage.warning('请选择问题类型')
    return
  }
  
  if (!contactForm.description.trim()) {
    ElMessage.warning('请描述您遇到的问题')
    return
  }
  
  if (!contactForm.contact.trim()) {
    ElMessage.warning('请提供您的联系方式')
    return
  }
  
  try {
    submitting.value = true
    
    // 这里应该调用提交反馈的 API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('您的问题已提交，我们会尽快处理并回复您')
    handleContactClose()
    
  } catch (error) {
    ElMessage.error('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

// 页面初始化
onMounted(() => {
  // 记录访问被拒绝的页面，用于分析
  const deniedPath = router.currentRoute.value.query.from as string
  if (deniedPath) {
    console.warn('Access denied to:', deniedPath)
  }
})
</script>

<style lang="scss" scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.error-content {
  max-width: 700px;
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
    color: #f5576c;
    line-height: 1;
    margin-bottom: 16px;
    text-shadow: 0 4px 8px rgba(245, 87, 108, 0.3);
    
    @media (max-width: 480px) {
      font-size: 80px;
    }
  }
  
  .error-icon {
    .el-icon {
      font-size: 64px;
      color: #e53e3e;
      
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
    margin: 0 0 16px 0;
    
    @media (max-width: 480px) {
      font-size: 14px;
    }
  }
}

.suggestions {
  text-align: left;
  max-width: 500px;
  margin: 0 auto 24px;
  
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

.permission-info {
  margin-bottom: 32px;
  
  .info-card {
    background: #f7fafc;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #e2e8f0;
    
    .info-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
      font-weight: 600;
      color: #2d3748;
      
      .el-icon {
        font-size: 20px;
        color: #4299e1;
      }
    }
    
    .info-content {
      .info-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #e2e8f0;
        
        &:last-child {
          border-bottom: none;
        }
        
        .label {
          color: #718096;
          font-size: 14px;
        }
        
        .value {
          color: #2d3748;
          font-weight: 500;
          font-size: 14px;
        }
      }
    }
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

.contact-section {
  margin-bottom: 32px;
  
  .contact-title {
    font-size: 16px;
    color: #4a5568;
    margin-bottom: 16px;
  }
  
  .contact-actions {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
  }
}

.accessible-pages {
  .pages-title {
    font-size: 16px;
    color: #4a5568;
    margin-bottom: 16px;
  }
  
  .pages-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
    max-width: 400px;
    margin: 0 auto;
    
    @media (max-width: 480px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  .page-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px 12px;
    background: #f7fafc;
    border-radius: 12px;
    text-decoration: none;
    color: #4a5568;
    transition: all 0.3s ease;
    border: 2px solid transparent;
    
    &:hover {
      background: #f5576c;
      color: white;
      transform: translateY(-2px);
      box-shadow: 0 8px 16px rgba(245, 87, 108, 0.3);
    }
    
    .el-icon {
      font-size: 24px;
    }
    
    span {
      font-size: 12px;
      font-weight: 500;
    }
  }
}

.help-content {
  h4 {
    color: #2d3748;
    margin: 0 0 12px 0;
    font-size: 16px;
  }
  
  ul, ol {
    margin: 0 0 20px 0;
    padding-left: 20px;
    
    li {
      color: #4a5568;
      font-size: 14px;
      line-height: 1.6;
      margin-bottom: 8px;
      
      strong {
        color: #2d3748;
      }
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
  
  .contact-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 100%;
      max-width: 200px;
    }
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
  
  .permission-info {
    .info-card {
      padding: 16px;
      
      .info-content {
        .info-item {
          flex-direction: column;
          align-items: flex-start;
          gap: 4px;
        }
      }
    }
  }
}
</style>