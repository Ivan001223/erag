<template>
  <div class="security-container">
    <!-- 页面头部 -->
    <div class="security-header">
      <h2>安全设置</h2>
      <p>管理您的账户安全和隐私设置</p>
    </div>

    <!-- 主要内容 -->
    <div class="security-content">
      <el-row :gutter="24">
        <!-- 左侧安全设置 -->
        <el-col :span="16">
          <!-- 密码设置 -->
          <el-card class="security-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>密码设置</span>
                <el-tag type="success" v-if="passwordStrong">强密码</el-tag>
                <el-tag type="warning" v-else>建议加强</el-tag>
              </div>
            </template>
            <div class="password-section">
              <div class="password-info">
                <div class="info-item">
                  <label>当前密码强度：</label>
                  <el-progress 
                    :percentage="passwordStrength" 
                    :color="getPasswordColor(passwordStrength)"
                    :show-text="false"
                  />
                </div>
                <div class="info-item">
                  <label>上次修改时间：</label>
                  <span>{{ formatDate(lastPasswordChange) }}</span>
                </div>
              </div>
              <el-button type="primary" @click="showChangePassword = true">
                <el-icon><Lock /></el-icon>
                修改密码
              </el-button>
            </div>
          </el-card>

          <!-- 两步验证 -->
          <el-card class="security-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>两步验证</span>
                <el-tag type="success" v-if="twoFactorEnabled">已启用</el-tag>
                <el-tag type="info" v-else>未启用</el-tag>
              </div>
            </template>
            <div class="two-factor-section">
              <div class="two-factor-info">
                <p v-if="!twoFactorEnabled">
                  启用两步验证可以为您的账户提供额外的安全保护。即使密码被泄露，攻击者也无法访问您的账户。
                </p>
                <p v-else>
                  两步验证已启用。您可以使用以下方式进行身份验证：
                </p>
                <div v-if="twoFactorEnabled" class="auth-methods">
                  <div class="method-item">
                    <el-icon><Message /></el-icon>
                    <span>短信验证码</span>
                    <el-tag size="small">主要</el-tag>
                  </div>
                  <div class="method-item">
                    <el-icon><Smartphone /></el-icon>
                    <span>身份验证器应用</span>
                    <el-tag size="small" type="info">备用</el-tag>
                  </div>
                </div>
              </div>
              <div class="two-factor-actions">
                <el-button 
                  v-if="!twoFactorEnabled" 
                  type="primary" 
                  @click="enableTwoFactor"
                >
                  启用两步验证
                </el-button>
                <div v-else class="enabled-actions">
                  <el-button @click="manageTwoFactor">管理验证方式</el-button>
                  <el-button type="danger" plain @click="disableTwoFactor">
                    禁用两步验证
                  </el-button>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 登录设备 -->
          <el-card class="security-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>登录设备</span>
                <el-button type="text" @click="refreshDevices">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </template>
            <div class="devices-section">
              <div class="device-list">
                <div v-for="device in loginDevices" :key="device.id" class="device-item">
                  <div class="device-icon">
                    <el-icon>
                      <component :is="getDeviceIcon(device.type)" />
                    </el-icon>
                  </div>
                  <div class="device-info">
                    <div class="device-name">{{ device.name }}</div>
                    <div class="device-details">
                      <span>{{ device.location }}</span>
                      <span>{{ formatDate(device.lastActive) }}</span>
                    </div>
                    <div class="device-status">
                      <el-tag v-if="device.current" type="success" size="small">当前设备</el-tag>
                      <el-tag v-else-if="device.active" type="info" size="small">活跃</el-tag>
                      <el-tag v-else type="info" size="small">离线</el-tag>
                    </div>
                  </div>
                  <div class="device-actions">
                    <el-button 
                      v-if="!device.current" 
                      type="danger" 
                      size="small" 
                      plain
                      @click="revokeDevice(device)"
                    >
                      移除
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 安全日志 -->
          <el-card class="security-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>安全日志</span>
                <el-button type="text" @click="viewAllLogs">
                  查看全部
                </el-button>
              </div>
            </template>
            <div class="security-logs">
              <div v-for="log in securityLogs" :key="log.id" class="log-item">
                <div class="log-icon">
                  <el-icon :class="getLogIconClass(log.type)">
                    <component :is="getLogIcon(log.type)" />
                  </el-icon>
                </div>
                <div class="log-content">
                  <div class="log-title">{{ log.title }}</div>
                  <div class="log-details">
                    <span>{{ log.location }}</span>
                    <span>{{ formatDate(log.timestamp) }}</span>
                  </div>
                </div>
                <div class="log-status">
                  <el-tag 
                    :type="log.success ? 'success' : 'danger'" 
                    size="small"
                  >
                    {{ log.success ? '成功' : '失败' }}
                  </el-tag>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧安全建议 -->
        <el-col :span="8">
          <!-- 安全评分 -->
          <el-card class="security-score-card" shadow="hover">
            <template #header>
              <span>安全评分</span>
            </template>
            <div class="security-score">
              <div class="score-circle">
                <el-progress 
                  type="circle" 
                  :percentage="securityScore" 
                  :width="120"
                  :color="getScoreColor(securityScore)"
                >
                  <template #default="{ percentage }">
                    <span class="score-text">{{ percentage }}</span>
                  </template>
                </el-progress>
              </div>
              <div class="score-description">
                <p v-if="securityScore >= 80">您的账户安全性很好！</p>
                <p v-else-if="securityScore >= 60">您的账户安全性一般，建议加强。</p>
                <p v-else>您的账户安全性较低，请立即加强！</p>
              </div>
            </div>
          </el-card>

          <!-- 安全建议 -->
          <el-card class="security-tips-card" shadow="hover">
            <template #header>
              <span>安全建议</span>
            </template>
            <div class="security-tips">
              <div v-for="tip in securityTips" :key="tip.id" class="tip-item">
                <div class="tip-icon">
                  <el-icon :class="tip.completed ? 'completed' : 'pending'">
                    <component :is="tip.completed ? 'Check' : 'Warning'" />
                  </el-icon>
                </div>
                <div class="tip-content">
                  <div class="tip-title">{{ tip.title }}</div>
                  <div class="tip-description">{{ tip.description }}</div>
                  <el-button 
                    v-if="!tip.completed" 
                    type="text" 
                    size="small"
                    @click="handleTip(tip)"
                  >
                    {{ tip.action }}
                  </el-button>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 紧急联系 -->
          <el-card class="emergency-card" shadow="hover">
            <template #header>
              <span>紧急情况</span>
            </template>
            <div class="emergency-content">
              <p>如果您发现账户异常活动或怀疑账户被盗用：</p>
              <div class="emergency-actions">
                <el-button type="danger" @click="emergencyLock">
                  <el-icon><Lock /></el-icon>
                  立即锁定账户
                </el-button>
                <el-button type="warning" @click="contactSupport">
                  <el-icon><Service /></el-icon>
                  联系客服
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 修改密码对话框 -->
    <el-dialog 
      v-model="showChangePassword" 
      title="修改密码" 
      width="500px"
      :before-close="handleClosePasswordDialog"
    >
      <el-form 
        ref="passwordFormRef" 
        :model="passwordForm" 
        :rules="passwordRules" 
        label-width="100px"
      >
        <el-form-item label="当前密码" prop="currentPassword">
          <el-input 
            v-model="passwordForm.currentPassword" 
            type="password" 
            show-password
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input 
            v-model="passwordForm.newPassword" 
            type="password" 
            show-password
            placeholder="请输入新密码"
            @input="checkPasswordStrength"
          />
          <div class="password-strength">
            <el-progress 
              :percentage="newPasswordStrength" 
              :color="getPasswordColor(newPasswordStrength)"
              :show-text="false"
              size="small"
            />
            <span class="strength-text">{{ getPasswordStrengthText(newPasswordStrength) }}</span>
          </div>
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="passwordForm.confirmPassword" 
            type="password" 
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showChangePassword = false">取消</el-button>
          <el-button type="primary" @click="changePassword" :loading="passwordChanging">
            确认修改
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Lock,
  Message,
  Smartphone,
  Refresh,
  Monitor,
  Iphone,
  Check,
  Warning,
  Service,
  User,
  Key,
  Shield
} from '@element-plus/icons-vue'

// 响应式数据
const showChangePassword = ref(false)
const passwordChanging = ref(false)
const twoFactorEnabled = ref(false)
const passwordStrong = ref(true)
const passwordStrength = ref(85)
const newPasswordStrength = ref(0)
const lastPasswordChange = ref('2024-01-10T08:00:00Z')
const securityScore = ref(78)

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const passwordFormRef = ref()

const loginDevices = ref([
  {
    id: 1,
    name: 'Windows PC - Chrome',
    type: 'desktop',
    location: '北京市',
    lastActive: '2024-01-15T10:30:00Z',
    current: true,
    active: true
  },
  {
    id: 2,
    name: 'iPhone 15 Pro',
    type: 'mobile',
    location: '上海市',
    lastActive: '2024-01-14T18:20:00Z',
    current: false,
    active: true
  },
  {
    id: 3,
    name: 'MacBook Pro - Safari',
    type: 'desktop',
    location: '深圳市',
    lastActive: '2024-01-12T14:15:00Z',
    current: false,
    active: false
  }
])

const securityLogs = ref([
  {
    id: 1,
    type: 'login',
    title: '账户登录',
    location: '北京市',
    timestamp: '2024-01-15T10:30:00Z',
    success: true
  },
  {
    id: 2,
    type: 'password',
    title: '密码修改',
    location: '北京市',
    timestamp: '2024-01-10T08:00:00Z',
    success: true
  },
  {
    id: 3,
    type: 'login',
    title: '登录尝试',
    location: '未知位置',
    timestamp: '2024-01-08T22:15:00Z',
    success: false
  }
])

const securityTips = ref([
  {
    id: 1,
    title: '启用两步验证',
    description: '为账户添加额外的安全保护',
    action: '立即启用',
    completed: false
  },
  {
    id: 2,
    title: '使用强密码',
    description: '密码应包含大小写字母、数字和特殊字符',
    action: '修改密码',
    completed: true
  },
  {
    id: 3,
    title: '定期检查登录设备',
    description: '移除不再使用的设备',
    action: '查看设备',
    completed: false
  }
])

// 表单验证规则
const passwordRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度不能少于8位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 计算属性和方法
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const getPasswordColor = (strength) => {
  if (strength >= 80) return '#67c23a'
  if (strength >= 60) return '#e6a23c'
  return '#f56c6c'
}

const getScoreColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const getPasswordStrengthText = (strength) => {
  if (strength >= 80) return '强'
  if (strength >= 60) return '中'
  if (strength >= 30) return '弱'
  return '很弱'
}

const getDeviceIcon = (type) => {
  return type === 'mobile' ? Iphone : Monitor
}

const getLogIcon = (type) => {
  const iconMap = {
    login: User,
    password: Key,
    security: Shield
  }
  return iconMap[type] || User
}

const getLogIconClass = (type) => {
  const classMap = {
    login: 'login-icon',
    password: 'password-icon',
    security: 'security-icon'
  }
  return classMap[type] || 'default-icon'
}

const checkPasswordStrength = () => {
  const password = passwordForm.newPassword
  let strength = 0
  
  if (password.length >= 8) strength += 25
  if (/[a-z]/.test(password)) strength += 25
  if (/[A-Z]/.test(password)) strength += 25
  if (/[0-9]/.test(password)) strength += 15
  if (/[^A-Za-z0-9]/.test(password)) strength += 10
  
  newPasswordStrength.value = Math.min(strength, 100)
}

const changePassword = async () => {
  try {
    await passwordFormRef.value.validate()
    passwordChanging.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    ElMessage.success('密码修改成功')
    showChangePassword.value = false
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    newPasswordStrength.value = 0
    lastPasswordChange.value = new Date().toISOString()
  } catch (error) {
    console.error('密码修改失败:', error)
  } finally {
    passwordChanging.value = false
  }
}

const handleClosePasswordDialog = () => {
  passwordForm.currentPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  newPasswordStrength.value = 0
  showChangePassword.value = false
}

const enableTwoFactor = () => {
  ElMessage.info('两步验证设置功能开发中...')
}

const manageTwoFactor = () => {
  ElMessage.info('管理验证方式功能开发中...')
}

const disableTwoFactor = async () => {
  try {
    await ElMessageBox.confirm(
      '禁用两步验证会降低您的账户安全性，确定要继续吗？',
      '确认禁用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    twoFactorEnabled.value = false
    ElMessage.success('两步验证已禁用')
  } catch {
    // 用户取消
  }
}

const refreshDevices = () => {
  ElMessage.success('设备列表已刷新')
}

const revokeDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      `确定要移除设备 "${device.name}" 吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    const index = loginDevices.value.findIndex(d => d.id === device.id)
    if (index > -1) {
      loginDevices.value.splice(index, 1)
      ElMessage.success('设备已移除')
    }
  } catch {
    // 用户取消
  }
}

const viewAllLogs = () => {
  ElMessage.info('查看全部安全日志功能开发中...')
}

const handleTip = (tip) => {
  if (tip.id === 1) {
    enableTwoFactor()
  } else if (tip.id === 2) {
    showChangePassword.value = true
  } else if (tip.id === 3) {
    // 滚动到设备部分
    document.querySelector('.devices-section')?.scrollIntoView({ behavior: 'smooth' })
  }
}

const emergencyLock = async () => {
  try {
    await ElMessageBox.confirm(
      '紧急锁定将立即注销所有设备并禁用账户，您需要联系客服解锁。确定要继续吗？',
      '紧急锁定账户',
      {
        confirmButtonText: '确定锁定',
        cancelButtonText: '取消',
        type: 'error'
      }
    )
    ElMessage.success('账户已紧急锁定，请联系客服解锁')
  } catch {
    // 用户取消
  }
}

const contactSupport = () => {
  ElMessage.info('客服联系功能开发中...')
}

// 生命周期
onMounted(() => {
  console.log('Security page mounted')
})
</script>

<style scoped>
.security-container {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.security-header {
  margin-bottom: 24px;
}

.security-header h2 {
  margin: 0 0 8px 0;
  color: #303133;
}

.security-header p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.security-content {
  gap: 20px;
}

.security-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.password-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.password-info {
  flex: 1;
  margin-right: 20px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.info-item label {
  width: 120px;
  color: #606266;
  font-size: 14px;
}

.info-item span {
  color: #303133;
  font-size: 14px;
}

.info-item .el-progress {
  flex: 1;
  margin-left: 12px;
}

.two-factor-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.two-factor-info {
  flex: 1;
  margin-right: 20px;
}

.two-factor-info p {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.auth-methods {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.method-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.enabled-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.devices-section {
  max-height: 400px;
  overflow-y: auto;
}

.device-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.device-item {
  display: flex;
  align-items: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.device-icon {
  width: 40px;
  height: 40px;
  background: #e1f3ff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  color: #409eff;
}

.device-info {
  flex: 1;
}

.device-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.device-details {
  display: flex;
  gap: 16px;
  color: #909399;
  font-size: 12px;
  margin-bottom: 4px;
}

.device-status {
  margin-top: 4px;
}

.device-actions {
  margin-left: 12px;
}

.security-logs {
  max-height: 300px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.log-item:last-child {
  border-bottom: none;
}

.log-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
}

.login-icon {
  background: #e1f3ff;
  color: #409eff;
}

.password-icon {
  background: #f0f9ff;
  color: #10b981;
}

.security-icon {
  background: #fef3e2;
  color: #f59e0b;
}

.log-content {
  flex: 1;
}

.log-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.log-details {
  display: flex;
  gap: 16px;
  color: #909399;
  font-size: 12px;
}

.log-status {
  margin-left: 12px;
}

.security-score-card {
  margin-bottom: 20px;
}

.security-score {
  text-align: center;
}

.score-circle {
  margin-bottom: 16px;
}

.score-text {
  font-size: 24px;
  font-weight: bold;
}

.score-description p {
  color: #606266;
  font-size: 14px;
  margin: 0;
}

.security-tips-card {
  margin-bottom: 20px;
}

.security-tips {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.tip-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.tip-icon.completed {
  background: #f0f9ff;
  color: #10b981;
}

.tip-icon.pending {
  background: #fef3e2;
  color: #f59e0b;
}

.tip-content {
  flex: 1;
}

.tip-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.tip-description {
  color: #606266;
  font-size: 12px;
  margin-bottom: 8px;
}

.emergency-card {
  border: 1px solid #f56c6c;
}

.emergency-content p {
  color: #606266;
  font-size: 14px;
  margin-bottom: 16px;
}

.emergency-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.strength-text {
  font-size: 12px;
  color: #909399;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>