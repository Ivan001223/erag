<template>
  <div class="forgot-password-container">
    <div class="forgot-password-form">
      <div class="form-header">
        <h2>找回密码</h2>
        <p>请输入您的邮箱或手机号，我们将发送验证码帮助您重置密码</p>
      </div>
      
      <!-- 步骤指示器 -->
      <el-steps :active="currentStep" align-center class="steps">
        <el-step title="验证身份" />
        <el-step title="重置密码" />
        <el-step title="完成" />
      </el-steps>
      
      <!-- 第一步：验证身份 -->
      <div v-show="currentStep === 0" class="step-content">
        <el-form
          ref="verifyFormRef"
          :model="verifyForm"
          :rules="verifyRules"
          size="large"
        >
          <!-- 验证方式选择 -->
          <el-form-item>
            <el-radio-group v-model="verifyType" class="verify-type-group">
              <el-radio-button label="email">邮箱验证</el-radio-button>
              <el-radio-button label="phone">手机验证</el-radio-button>
            </el-radio-group>
          </el-form-item>
          
          <!-- 邮箱验证 -->
          <template v-if="verifyType === 'email'">
            <el-form-item prop="email">
              <el-input
                v-model="verifyForm.email"
                placeholder="请输入注册邮箱"
                prefix-icon="Message"
                clearable
              />
            </el-form-item>
            
            <el-form-item prop="emailCode">
              <div class="code-input-group">
                <el-input
                  v-model="verifyForm.emailCode"
                  placeholder="请输入邮箱验证码"
                  prefix-icon="Key"
                  clearable
                />
                <el-button
                  :disabled="emailCodeDisabled"
                  :loading="sendingEmailCode"
                  @click="sendEmailCode"
                  class="code-btn"
                >
                  {{ emailCodeText }}
                </el-button>
              </div>
            </el-form-item>
          </template>
          
          <!-- 手机验证 -->
          <template v-if="verifyType === 'phone'">
            <el-form-item prop="phone">
              <el-input
                v-model="verifyForm.phone"
                placeholder="请输入注册手机号"
                prefix-icon="Phone"
                clearable
              />
            </el-form-item>
            
            <el-form-item prop="phoneCode">
              <div class="code-input-group">
                <el-input
                  v-model="verifyForm.phoneCode"
                  placeholder="请输入手机验证码"
                  prefix-icon="Key"
                  clearable
                />
                <el-button
                  :disabled="phoneCodeDisabled"
                  :loading="sendingPhoneCode"
                  @click="sendPhoneCode"
                  class="code-btn"
                >
                  {{ phoneCodeText }}
                </el-button>
              </div>
            </el-form-item>
          </template>
          
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="verifying"
              @click="handleVerify"
              class="action-btn"
            >
              {{ verifying ? '验证中...' : '验证身份' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 第二步：重置密码 -->
      <div v-show="currentStep === 1" class="step-content">
        <el-form
          ref="resetFormRef"
          :model="resetForm"
          :rules="resetRules"
          size="large"
        >
          <el-form-item prop="newPassword">
            <el-input
              v-model="resetForm.newPassword"
              type="password"
              placeholder="请输入新密码"
              prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
          
          <el-form-item prop="confirmPassword">
            <el-input
              v-model="resetForm.confirmPassword"
              type="password"
              placeholder="请确认新密码"
              prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
          
          <el-form-item>
            <div class="button-group">
              <el-button @click="goBack" class="back-btn">
                返回上一步
              </el-button>
              <el-button
                type="primary"
                :loading="resetting"
                @click="handleReset"
                class="action-btn"
              >
                {{ resetting ? '重置中...' : '重置密码' }}
              </el-button>
            </div>
          </el-form-item>
        </el-form>
        
        <!-- 密码强度提示 -->
        <div v-if="showPasswordStrength" class="password-strength">
          <div class="strength-header">
            <span>密码强度：</span>
            <span :class="passwordStrengthClass">{{ passwordStrengthText }}</span>
          </div>
          <div class="strength-bar">
            <div 
              class="strength-fill"
              :class="passwordStrengthClass"
              :style="{ width: passwordStrengthPercent + '%' }"
            ></div>
          </div>
          <div class="strength-tips">
            <div class="tip-item" :class="{ active: hasLowerCase }">
              <el-icon><Check v-if="hasLowerCase" /><Close v-else /></el-icon>
              包含小写字母
            </div>
            <div class="tip-item" :class="{ active: hasUpperCase }">
              <el-icon><Check v-if="hasUpperCase" /><Close v-else /></el-icon>
              包含大写字母
            </div>
            <div class="tip-item" :class="{ active: hasNumber }">
              <el-icon><Check v-if="hasNumber" /><Close v-else /></el-icon>
              包含数字
            </div>
            <div class="tip-item" :class="{ active: hasSpecialChar }">
              <el-icon><Check v-if="hasSpecialChar" /><Close v-else /></el-icon>
              包含特殊字符
            </div>
            <div class="tip-item" :class="{ active: hasMinLength }">
              <el-icon><Check v-if="hasMinLength" /><Close v-else /></el-icon>
              至少8位字符
            </div>
          </div>
        </div>
      </div>
      
      <!-- 第三步：完成 -->
      <div v-show="currentStep === 2" class="step-content success-content">
        <div class="success-icon">
          <el-icon><SuccessFilled /></el-icon>
        </div>
        <h3>密码重置成功！</h3>
        <p>您的密码已成功重置，请使用新密码登录</p>
        
        <div class="success-actions">
          <el-button type="primary" size="large" @click="goToLogin" class="action-btn">
            立即登录
          </el-button>
        </div>
      </div>
      
      <!-- 返回登录链接 -->
      <div class="form-footer">
        <router-link to="/login" class="back-to-login">
          <el-icon><ArrowLeft /></el-icon>
          返回登录
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import {
  Check, Close, SuccessFilled, ArrowLeft
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 表单引用
const verifyFormRef = ref<FormInstance>()
const resetFormRef = ref<FormInstance>()

// 当前步骤
const currentStep = ref(0)

// 验证方式
const verifyType = ref('email')

// 状态
const verifying = ref(false)
const resetting = ref(false)
const sendingEmailCode = ref(false)
const sendingPhoneCode = ref(false)

// 验证码倒计时
const emailCodeCountdown = ref(0)
const phoneCodeCountdown = ref(0)

// 验证表单
const verifyForm = reactive({
  email: '',
  phone: '',
  emailCode: '',
  phoneCode: ''
})

// 重置表单
const resetForm = reactive({
  newPassword: '',
  confirmPassword: ''
})

// 验证令牌（从后端获取）
const resetToken = ref('')

// 自定义验证规则
const validateEmail = (rule: any, value: string, callback: any) => {
  if (verifyType.value === 'email') {
    if (!value) {
      callback(new Error('请输入邮箱地址'))
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      callback(new Error('请输入有效的邮箱地址'))
    } else {
      callback()
    }
  } else {
    callback()
  }
}

const validatePhone = (rule: any, value: string, callback: any) => {
  if (verifyType.value === 'phone') {
    if (!value) {
      callback(new Error('请输入手机号码'))
    } else if (!/^1[3-9]\d{9}$/.test(value)) {
      callback(new Error('请输入有效的手机号码'))
    } else {
      callback()
    }
  } else {
    callback()
  }
}

const validateEmailCode = (rule: any, value: string, callback: any) => {
  if (verifyType.value === 'email') {
    if (!value) {
      callback(new Error('请输入邮箱验证码'))
    } else if (value.length !== 6) {
      callback(new Error('验证码长度为6位'))
    } else {
      callback()
    }
  } else {
    callback()
  }
}

const validatePhoneCode = (rule: any, value: string, callback: any) => {
  if (verifyType.value === 'phone') {
    if (!value) {
      callback(new Error('请输入手机验证码'))
    } else if (value.length !== 6) {
      callback(new Error('验证码长度为6位'))
    } else {
      callback()
    }
  } else {
    callback()
  }
}

const validateNewPassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入新密码'))
  } else if (value.length < 8) {
    callback(new Error('密码长度不能少于8位'))
  } else if (passwordStrength.value < 3) {
    callback(new Error('密码强度太弱，请包含大小写字母、数字和特殊字符'))
  } else {
    callback()
  }
}

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请确认新密码'))
  } else if (value !== resetForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

// 表单验证规则
const verifyRules: FormRules = {
  email: [{ validator: validateEmail, trigger: 'blur' }],
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  emailCode: [{ validator: validateEmailCode, trigger: 'blur' }],
  phoneCode: [{ validator: validatePhoneCode, trigger: 'blur' }]
}

const resetRules: FormRules = {
  newPassword: [{ validator: validateNewPassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

// 密码强度检测
const hasLowerCase = computed(() => /[a-z]/.test(resetForm.newPassword))
const hasUpperCase = computed(() => /[A-Z]/.test(resetForm.newPassword))
const hasNumber = computed(() => /\d/.test(resetForm.newPassword))
const hasSpecialChar = computed(() => /[!@#$%^&*(),.?":{}|<>]/.test(resetForm.newPassword))
const hasMinLength = computed(() => resetForm.newPassword.length >= 8)

const passwordStrength = computed(() => {
  let strength = 0
  if (hasLowerCase.value) strength++
  if (hasUpperCase.value) strength++
  if (hasNumber.value) strength++
  if (hasSpecialChar.value) strength++
  if (hasMinLength.value) strength++
  return strength
})

const passwordStrengthPercent = computed(() => {
  return (passwordStrength.value / 5) * 100
})

const passwordStrengthText = computed(() => {
  if (passwordStrength.value <= 1) return '很弱'
  if (passwordStrength.value <= 2) return '弱'
  if (passwordStrength.value <= 3) return '中等'
  if (passwordStrength.value <= 4) return '强'
  return '很强'
})

const passwordStrengthClass = computed(() => {
  if (passwordStrength.value <= 1) return 'very-weak'
  if (passwordStrength.value <= 2) return 'weak'
  if (passwordStrength.value <= 3) return 'medium'
  if (passwordStrength.value <= 4) return 'strong'
  return 'very-strong'
})

const showPasswordStrength = computed(() => {
  return resetForm.newPassword.length > 0
})

// 验证码按钮状态
const emailCodeDisabled = computed(() => {
  return !verifyForm.email || emailCodeCountdown.value > 0 || sendingEmailCode.value
})

const phoneCodeDisabled = computed(() => {
  return !verifyForm.phone || phoneCodeCountdown.value > 0 || sendingPhoneCode.value
})

const emailCodeText = computed(() => {
  return emailCodeCountdown.value > 0 ? `${emailCodeCountdown.value}s` : '获取验证码'
})

const phoneCodeText = computed(() => {
  return phoneCodeCountdown.value > 0 ? `${phoneCodeCountdown.value}s` : '获取验证码'
})

// 发送邮箱验证码
const sendEmailCode = async () => {
  if (!verifyForm.email) {
    ElMessage.warning('请先输入邮箱地址')
    return
  }
  
  try {
    sendingEmailCode.value = true
    
    // 这里应该调用发送邮箱验证码的 API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('验证码已发送到您的邮箱')
    
    // 开始倒计时
    emailCodeCountdown.value = 60
    const timer = setInterval(() => {
      emailCodeCountdown.value--
      if (emailCodeCountdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
    
  } catch (error) {
    ElMessage.error('验证码发送失败，请稍后重试')
  } finally {
    sendingEmailCode.value = false
  }
}

// 发送手机验证码
const sendPhoneCode = async () => {
  if (!verifyForm.phone) {
    ElMessage.warning('请先输入手机号码')
    return
  }
  
  try {
    sendingPhoneCode.value = true
    
    // 这里应该调用发送手机验证码的 API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('验证码已发送到您的手机')
    
    // 开始倒计时
    phoneCodeCountdown.value = 60
    const timer = setInterval(() => {
      phoneCodeCountdown.value--
      if (phoneCodeCountdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
    
  } catch (error) {
    ElMessage.error('验证码发送失败，请稍后重试')
  } finally {
    sendingPhoneCode.value = false
  }
}

// 处理身份验证
const handleVerify = async () => {
  if (!verifyFormRef.value) return
  
  try {
    await verifyFormRef.value.validate()
    
    verifying.value = true
    
    // 这里应该调用身份验证 API
    const verifyData = {
      type: verifyType.value,
      email: verifyType.value === 'email' ? verifyForm.email : undefined,
      phone: verifyType.value === 'phone' ? verifyForm.phone : undefined,
      code: verifyType.value === 'email' ? verifyForm.emailCode : verifyForm.phoneCode
    }
    
    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 假设验证成功，获取重置令牌
    resetToken.value = 'mock-reset-token'
    
    ElMessage.success('身份验证成功')
    currentStep.value = 1
    
  } catch (error: any) {
    ElMessage.error(error.message || '身份验证失败，请检查验证码')
  } finally {
    verifying.value = false
  }
}

// 处理密码重置
const handleReset = async () => {
  if (!resetFormRef.value) return
  
  try {
    await resetFormRef.value.validate()
    
    resetting.value = true
    
    // 这里应该调用密码重置 API
    const resetData = {
      token: resetToken.value,
      newPassword: resetForm.newPassword
    }
    
    await userStore.resetPassword(resetData)
    
    ElMessage.success('密码重置成功')
    currentStep.value = 2
    
  } catch (error: any) {
    ElMessage.error(error.message || '密码重置失败，请稍后重试')
  } finally {
    resetting.value = false
  }
}

// 返回上一步
const goBack = () => {
  currentStep.value = 0
}

// 跳转到登录页面
const goToLogin = () => {
  router.push('/login?message=password-reset-success')
}

// 监听验证方式变化，清空表单
watch(
  () => verifyType.value,
  () => {
    verifyForm.email = ''
    verifyForm.phone = ''
    verifyForm.emailCode = ''
    verifyForm.phoneCode = ''
    verifyFormRef.value?.clearValidate()
  }
)

// 监听新密码变化，重新验证确认密码
watch(
  () => resetForm.newPassword,
  () => {
    if (resetForm.confirmPassword) {
      resetFormRef.value?.validateField('confirmPassword')
    }
  }
)
</script>

<style lang="scss" scoped>
.forgot-password-container {
  max-width: 500px;
  margin: 0 auto;
}

.forgot-password-form {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 32px;
  box-shadow: var(--el-box-shadow-light);
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
  
  h2 {
    margin: 0 0 8px 0;
    color: var(--el-text-color-primary);
    font-size: 24px;
    font-weight: 600;
  }
  
  p {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: 14px;
    line-height: 1.5;
  }
}

.steps {
  margin-bottom: 32px;
}

.step-content {
  min-height: 200px;
}

.verify-type-group {
  width: 100%;
  display: flex;
  
  :deep(.el-radio-button) {
    flex: 1;
    
    .el-radio-button__inner {
      width: 100%;
    }
  }
}

.code-input-group {
  display: flex;
  gap: 8px;
  
  .el-input {
    flex: 1;
  }
  
  .code-btn {
    flex-shrink: 0;
    width: 100px;
  }
}

.action-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
}

.button-group {
  display: flex;
  gap: 12px;
  
  .back-btn {
    flex: 1;
    height: 44px;
  }
  
  .action-btn {
    flex: 2;
  }
}

.password-strength {
  margin-top: 16px;
  padding: 16px;
  background: var(--el-fill-color-extra-light);
  border-radius: 6px;
  
  .strength-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 14px;
    
    .very-weak {
      color: var(--el-color-error);
    }
    
    .weak {
      color: var(--el-color-warning);
    }
    
    .medium {
      color: var(--el-color-info);
    }
    
    .strong {
      color: var(--el-color-success);
    }
    
    .very-strong {
      color: var(--el-color-success);
      font-weight: 600;
    }
  }
  
  .strength-bar {
    height: 4px;
    background: var(--el-fill-color-light);
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 12px;
    
    .strength-fill {
      height: 100%;
      transition: all 0.3s ease;
      
      &.very-weak {
        background: var(--el-color-error);
      }
      
      &.weak {
        background: var(--el-color-warning);
      }
      
      &.medium {
        background: var(--el-color-info);
      }
      
      &.strong {
        background: var(--el-color-success);
      }
      
      &.very-strong {
        background: linear-gradient(90deg, var(--el-color-success), #52c41a);
      }
    }
  }
  
  .strength-tips {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    
    .tip-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      
      &.active {
        color: var(--el-color-success);
      }
      
      .el-icon {
        font-size: 14px;
      }
    }
  }
}

.success-content {
  text-align: center;
  padding: 32px 0;
  
  .success-icon {
    margin-bottom: 16px;
    
    .el-icon {
      font-size: 64px;
      color: var(--el-color-success);
    }
  }
  
  h3 {
    margin: 0 0 8px 0;
    color: var(--el-text-color-primary);
    font-size: 20px;
    font-weight: 600;
  }
  
  p {
    margin: 0 0 24px 0;
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }
  
  .success-actions {
    .action-btn {
      max-width: 200px;
    }
  }
}

.form-footer {
  text-align: center;
  margin-top: 24px;
  
  .back-to-login {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--el-color-primary);
    text-decoration: none;
    font-size: 14px;
    
    &:hover {
      text-decoration: underline;
    }
    
    .el-icon {
      font-size: 16px;
    }
  }
}

// 响应式设计
@media (max-width: 480px) {
  .forgot-password-form {
    padding: 24px 16px;
  }
  
  .form-header {
    margin-bottom: 24px;
    
    h2 {
      font-size: 20px;
    }
  }
  
  .steps {
    margin-bottom: 24px;
  }
  
  .code-input-group {
    flex-direction: column;
    
    .code-btn {
      width: 100%;
    }
  }
  
  .button-group {
    flex-direction: column;
    
    .back-btn,
    .action-btn {
      flex: none;
    }
  }
  
  .password-strength {
    .strength-tips {
      grid-template-columns: 1fr;
    }
  }
}
</style>