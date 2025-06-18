<template>
  <div class="app-footer">
    <div class="footer-content">
      <!-- 左侧信息 -->
      <div class="footer-left">
        <span class="copyright">
          © {{ currentYear }} ERAG - Enterprise Retrieval Augmented Generation
        </span>
        <span class="version">
          v{{ version }}
        </span>
      </div>
      
      <!-- 中间状态信息 -->
      <div class="footer-center">
        <!-- 系统状态 -->
        <div class="status-item">
          <el-icon class="status-icon" :class="systemStatus.class">
            <component :is="systemStatus.icon" />
          </el-icon>
          <span class="status-text">{{ systemStatus.text }}</span>
        </div>
        
        <!-- 连接状态 -->
        <div class="status-item">
          <el-icon class="status-icon" :class="connectionStatus.class">
            <component :is="connectionStatus.icon" />
          </el-icon>
          <span class="status-text">{{ connectionStatus.text }}</span>
        </div>
        
        <!-- 数据库状态 -->
        <div class="status-item">
          <el-icon class="status-icon" :class="databaseStatus.class">
            <component :is="databaseStatus.icon" />
          </el-icon>
          <span class="status-text">{{ databaseStatus.text }}</span>
        </div>
      </div>
      
      <!-- 右侧链接 -->
      <div class="footer-right">
        <el-button type="primary" link size="small" @click="openHelp">
          <el-icon><QuestionFilled /></el-icon>
          帮助文档
        </el-button>
        
        <el-button type="primary" link size="small" @click="openFeedback">
          <el-icon><ChatDotRound /></el-icon>
          意见反馈
        </el-button>
        
        <el-button type="primary" link size="small" @click="openAbout">
          <el-icon><InfoFilled /></el-icon>
          关于我们
        </el-button>
        
        <!-- 主题切换 -->
        <el-tooltip :content="isDark ? '切换到亮色主题' : '切换到暗色主题'">
          <el-button 
            type="primary" 
            link 
            size="small" 
            @click="toggleTheme"
            class="theme-toggle"
          >
            <el-icon>
              <Sunny v-if="isDark" />
              <Moon v-else />
            </el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>
    
    <!-- 系统信息弹窗 -->
    <el-dialog
      v-model="aboutDialogVisible"
      title="关于 ERAG"
      width="500px"
      :show-close="true"
    >
      <div class="about-content">
        <div class="about-logo">
          <img src="/logo.svg" alt="ERAG" class="logo-image" />
          <h3>ERAG</h3>
          <p class="subtitle">Enterprise Retrieval Augmented Generation</p>
        </div>
        
        <div class="about-info">
          <div class="info-item">
            <span class="label">版本号：</span>
            <span class="value">{{ version }}</span>
          </div>
          <div class="info-item">
            <span class="label">构建时间：</span>
            <span class="value">{{ buildTime }}</span>
          </div>
          <div class="info-item">
            <span class="label">技术栈：</span>
            <span class="value">Vue 3 + TypeScript + Element Plus</span>
          </div>
          <div class="info-item">
            <span class="label">后端服务：</span>
            <span class="value">FastAPI + Neo4j + Redis</span>
          </div>
        </div>
        
        <div class="about-description">
          <p>
            ERAG 是一个企业级的检索增强生成系统，结合了知识图谱、向量数据库和大语言模型，
            为企业提供智能化的知识管理和问答服务。
          </p>
        </div>
        
        <div class="about-links">
          <el-button type="primary" @click="openGithub">
            <el-icon><Link /></el-icon>
            GitHub 仓库
          </el-button>
          <el-button @click="openDocs">
            <el-icon><Document /></el-icon>
            使用文档
          </el-button>
        </div>
      </div>
    </el-dialog>
    
    <!-- 反馈弹窗 -->
    <el-dialog
      v-model="feedbackDialogVisible"
      title="意见反馈"
      width="600px"
      :show-close="true"
    >
      <el-form 
        ref="feedbackFormRef"
        :model="feedbackForm"
        :rules="feedbackRules"
        label-width="80px"
      >
        <el-form-item label="反馈类型" prop="type">
          <el-select v-model="feedbackForm.type" placeholder="请选择反馈类型">
            <el-option label="功能建议" value="feature" />
            <el-option label="问题反馈" value="bug" />
            <el-option label="使用咨询" value="question" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="标题" prop="title">
          <el-input v-model="feedbackForm.title" placeholder="请输入反馈标题" />
        </el-form-item>
        
        <el-form-item label="详细描述" prop="content">
          <el-input
            v-model="feedbackForm.content"
            type="textarea"
            :rows="6"
            placeholder="请详细描述您的问题或建议..."
          />
        </el-form-item>
        
        <el-form-item label="联系方式" prop="contact">
          <el-input v-model="feedbackForm.contact" placeholder="邮箱或电话（可选）" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="feedbackDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitFeedback" :loading="submittingFeedback">
          提交反馈
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  QuestionFilled, ChatDotRound, InfoFilled, Sunny, Moon,
  SuccessFilled, WarningFilled, CircleCloseFilled,
  Link, Document, Connection
} from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
// 当前年份
const currentYear = new Date().getFullYear()

// 版本信息
const version = ref('1.0.0')
const buildTime = ref('2024-01-15 10:30:00')

// 主题状态
const isDark = computed(() => appStore.isDark)

// 系统状态
const systemStatus = computed(() => {
  return {
    icon: 'SuccessFilled',
    class: 'status-success',
    text: '系统正常'
  }
})

// 连接状态
const connectionStatus = computed(() => {
  return {
    icon: 'Connection',
    class: 'status-success',
    text: '连接正常'
  }
})

// 数据库状态
const databaseStatus = computed(() => {
  return {
    icon: 'SuccessFilled',
    class: 'status-success',
    text: '数据库正常'
  }
})

// 弹窗状态
const aboutDialogVisible = ref(false)
const feedbackDialogVisible = ref(false)
const submittingFeedback = ref(false)

// 反馈表单
const feedbackFormRef = ref<FormInstance>()
const feedbackForm = reactive({
  type: '',
  title: '',
  content: '',
  contact: ''
})

const feedbackRules: FormRules = {
  type: [
    { required: true, message: '请选择反馈类型', trigger: 'change' }
  ],
  title: [
    { required: true, message: '请输入反馈标题', trigger: 'blur' },
    { min: 5, max: 50, message: '标题长度应在 5 到 50 个字符', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入详细描述', trigger: 'blur' },
    { min: 10, max: 500, message: '描述长度应在 10 到 500 个字符', trigger: 'blur' }
  ]
}

// 切换主题
const toggleTheme = () => {
  appStore.toggleTheme()
}

// 打开帮助
const openHelp = () => {
  window.open('/help', '_blank')
}

// 打开反馈
const openFeedback = () => {
  feedbackDialogVisible.value = true
}

// 打开关于
const openAbout = () => {
  aboutDialogVisible.value = true
}

// 打开 GitHub
const openGithub = () => {
  window.open('https://github.com/your-org/erag', '_blank')
}

// 打开文档
const openDocs = () => {
  window.open('/docs', '_blank')
}

// 提交反馈
const submitFeedback = async () => {
  if (!feedbackFormRef.value) return
  
  try {
    await feedbackFormRef.value.validate()
    
    submittingFeedback.value = true
    
    // 这里应该调用 API 提交反馈
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('反馈提交成功，感谢您的建议！')
    feedbackDialogVisible.value = false
    
    // 重置表单
    feedbackFormRef.value.resetFields()
    
  } catch (error) {
    console.error('反馈提交失败:', error)
  } finally {
    submittingFeedback.value = false
  }
}
</script>

<style lang="scss" scoped>
.app-footer {
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-lighter);
  padding: 0 16px;
  height: 100%;
  display: flex;
  align-items: center;
}

.footer-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  font-size: 12px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--el-text-color-secondary);
  
  .copyright {
    font-weight: 400;
  }
  
  .version {
    padding: 2px 6px;
    background: var(--el-fill-color-light);
    border-radius: 2px;
    font-size: 11px;
    color: var(--el-text-color-regular);
  }
}

.footer-center {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
  
  .status-icon {
    font-size: 12px;
    
    &.status-success {
      color: var(--el-color-success);
    }
    
    &.status-warning {
      color: var(--el-color-warning);
    }
    
    &.status-error {
      color: var(--el-color-error);
    }
  }
  
  .status-text {
    color: var(--el-text-color-regular);
    font-size: 11px;
  }
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .el-button {
    font-size: 11px;
    padding: 4px 8px;
    
    .el-icon {
      font-size: 12px;
    }
  }
  
  .theme-toggle {
    .el-icon {
      font-size: 14px;
    }
  }
}

// 关于弹窗样式
.about-content {
  text-align: center;
  
  .about-logo {
    margin-bottom: 24px;
    
    .logo-image {
      width: 64px;
      height: 64px;
      margin-bottom: 12px;
    }
    
    h3 {
      margin: 0 0 8px 0;
      color: var(--el-text-color-primary);
      font-size: 24px;
      font-weight: 600;
    }
    
    .subtitle {
      margin: 0;
      color: var(--el-text-color-secondary);
      font-size: 14px;
    }
  }
  
  .about-info {
    text-align: left;
    margin-bottom: 24px;
    
    .info-item {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid var(--el-border-color-lighter);
      
      &:last-child {
        border-bottom: none;
      }
      
      .label {
        color: var(--el-text-color-regular);
        font-weight: 500;
      }
      
      .value {
        color: var(--el-text-color-primary);
      }
    }
  }
  
  .about-description {
    text-align: left;
    margin-bottom: 24px;
    
    p {
      margin: 0;
      color: var(--el-text-color-regular);
      line-height: 1.6;
    }
  }
  
  .about-links {
    display: flex;
    justify-content: center;
    gap: 12px;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .footer-content {
    font-size: 11px;
  }
  
  .footer-center {
    gap: 12px;
    
    .status-item {
      .status-text {
        display: none;
      }
    }
  }
  
  .footer-right {
    gap: 4px;
    
    .el-button {
      font-size: 10px;
      padding: 2px 6px;
      
      span {
        display: none;
      }
    }
  }
}

@media (max-width: 480px) {
  .app-footer {
    padding: 0 8px;
  }
  
  .footer-left {
    gap: 8px;
    
    .copyright {
      display: none;
    }
  }
  
  .footer-center {
    gap: 8px;
    
    .status-item:not(:first-child) {
      display: none;
    }
  }
  
  .footer-right {
    .el-button:not(.theme-toggle) {
      display: none;
    }
  }
}
</style>