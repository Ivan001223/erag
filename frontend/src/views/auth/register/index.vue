<template>
  <div class="register-container">
    <div class="register-form">
      <div class="form-header">
        <h2>创建账户</h2>
        <p>加入 ERAG，开启智能知识管理之旅</p>
      </div>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        size="large"
        @keyup.enter="handleRegister"
      >
        <!-- 用户名 -->
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            clearable
          />
        </el-form-item>
        
        <!-- 邮箱 -->
        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="请输入邮箱地址"
            prefix-icon="Message"
            clearable
          />
        </el-form-item>
        
        <!-- 手机号 -->
        <el-form-item prop="phone">
          <el-input
            v-model="registerForm.phone"
            placeholder="请输入手机号码"
            prefix-icon="Phone"
            clearable
          />
        </el-form-item>
        
        <!-- 密码 -->
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>
        
        <!-- 确认密码 -->
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请确认密码"
            prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>
        
        <!-- 邮箱验证码 -->
        <el-form-item prop="emailCode">
          <div class="code-input-group">
            <el-input
              v-model="registerForm.emailCode"
              placeholder="请输入邮箱验证码"
              prefix-icon="Message"
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
        
        <!-- 手机验证码 -->
        <el-form-item prop="phoneCode">
          <div class="code-input-group">
            <el-input
              v-model="registerForm.phoneCode"
              placeholder="请输入手机验证码"
              prefix-icon="Phone"
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
        
        <!-- 邀请码（可选） -->
        <el-form-item prop="inviteCode">
          <el-input
            v-model="registerForm.inviteCode"
            placeholder="邀请码（可选）"
            prefix-icon="Ticket"
            clearable
          />
        </el-form-item>
        
        <!-- 用户协议 -->
        <el-form-item prop="agreement">
          <el-checkbox v-model="registerForm.agreement">
            我已阅读并同意
            <el-button type="primary" link @click="showTerms">
              《用户协议》
            </el-button>
            和
            <el-button type="primary" link @click="showPrivacy">
              《隐私政策》
            </el-button>
          </el-checkbox>
        </el-form-item>
        
        <!-- 注册按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="registering"
            @click="handleRegister"
            class="register-btn"
          >
            {{ registering ? '注册中...' : '立即注册' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 登录链接 -->
      <div class="form-footer">
        <span>已有账户？</span>
        <router-link to="/login" class="login-link">
          立即登录
        </router-link>
      </div>
    </div>
    
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
    
    <!-- 用户协议弹窗 -->
    <el-dialog
      v-model="termsDialogVisible"
      title="用户协议"
      width="600px"
      :show-close="true"
    >
      <div class="terms-content">
        <h3>1. 服务条款</h3>
        <p>欢迎使用 ERAG 企业级检索增强生成系统。在使用本服务前，请仔细阅读本协议。</p>
        
        <h3>2. 用户权利与义务</h3>
        <p>用户有权使用本系统提供的各项功能，同时需要遵守相关法律法规和本协议的约定。</p>
        
        <h3>3. 数据安全与隐私</h3>
        <p>我们承诺保护用户的数据安全和隐私，不会未经授权泄露用户信息。</p>
        
        <h3>4. 服务变更与终止</h3>
        <p>我们保留在必要时修改或终止服务的权利，会提前通知用户。</p>
        
        <h3>5. 免责声明</h3>
        <p>在法律允许的范围内，我们对因使用本服务而产生的损失不承担责任。</p>
      </div>
      
      <template #footer>
        <el-button @click="termsDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="acceptTerms">同意并关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 隐私政策弹窗 -->
    <el-dialog
      v-model="privacyDialogVisible"
      title="隐私政策"
      width="600px"
      :show-close="true"
    >
      <div class="privacy-content">
        <h3>1. 信息收集</h3>
        <p>我们只收集为提供服务所必需的用户信息，包括账户信息、使用数据等。</p>
        
        <h3>2. 信息使用</h3>
        <p>收集的信息仅用于提供和改进服务，不会用于其他商业目的。</p>
        
        <h3>3. 信息共享</h3>
        <p>除法律要求外，我们不会与第三方共享用户的个人信息。</p>
        
        <h3>4. 数据安全</h3>
        <p>我们采用行业标准的安全措施保护用户数据，防止未经授权的访问。</p>
        
        <h3>5. 用户权利</h3>
        <p>用户有权查看、修改或删除自己的个人信息。</p>
      </div>
      
      <template #footer>
        <el-button @click="privacyDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="acceptPrivacy">同意并关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 表单引用
const registerFormRef = ref<FormInstance>()

// 注册状态
const registering = ref(false)
const sendingEmailCode = ref(false)
const sendingPhoneCode = ref(false)

// 验证码倒计时
const emailCodeCountdown = ref(0)
const phoneCodeCountdown = ref(0)

// 弹窗状态
const termsDialogVisible = ref(false)
const privacyDialogVisible = ref(false)

// 注册表单
const registerForm = reactive({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  emailCode: '',
  phoneCode: '',
  inviteCode: '',
  agreement: false
})

// 自定义验证规则
const validateUsername = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入用户名'))
  } else if (value.length < 3 || value.length > 20) {
    callback(new Error('用户名长度应在3-20个字符之间'))
  } else if (!/^[a-zA-Z0-9_]+$/.test(value)) {
    callback(new Error('用户名只能包含字母、数字和下划线'))
  } else {
    callback()
  }
}

const validateEmail = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入邮箱地址'))
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
    callback(new Error('请输入有效的邮箱地址'))
  } else {
    callback()
  }
}

const validatePhone = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入手机号码'))
  } else if (!/^1[3-9]\d{9}$/.test(value)) {
    callback(new Error('请输入有效的手机号码'))
  } else {
    callback()
  }
}

const validatePassword = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入密码'))
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
    callback(new Error('请确认密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const validateAgreement = (rule: any, value: boolean, callback: any) => {
  if (!value) {
    callback(new Error('请阅读并同意用户协议和隐私政策'))
  } else {
    callback()
  }
}

// 表单验证规则
const registerRules: FormRules = {
  username: [{ validator: validateUsername, trigger: 'blur' }],
  email: [{ validator: validateEmail, trigger: 'blur' }],
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
  emailCode: [
    { required: true, message: '请输入邮箱验证码', trigger: 'blur' },
    { len: 6, message: '验证码长度为6位', trigger: 'blur' }
  ],
  phoneCode: [
    { required: true, message: '请输入手机验证码', trigger: 'blur' },
    { len: 6, message: '验证码长度为6位', trigger: 'blur' }
  ],
  agreement: [{ validator: validateAgreement, trigger: 'change' }]
}

// 密码强度检测
const hasLowerCase = computed(() => /[a-z]/.test(registerForm.password))
const hasUpperCase = computed(() => /[A-Z]/.test(registerForm.password))
const hasNumber = computed(() => /\d/.test(registerForm.password))
const hasSpecialChar = computed(() => /[!@#$%^&*(),.?":{}|<>]/.test(registerForm.password))
const hasMinLength = computed(() => registerForm.password.length >= 8)

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
  return registerForm.password.length > 0
})

// 验证码按钮状态
const emailCodeDisabled = computed(() => {
  return !registerForm.email || emailCodeCountdown.value > 0 || sendingEmailCode.value
})

const phoneCodeDisabled = computed(() => {
  return !registerForm.phone || phoneCodeCountdown.value > 0 || sendingPhoneCode.value
})

const emailCodeText = computed(() => {
  return emailCodeCountdown.value > 0 ? `${emailCodeCountdown.value}s` : '获取验证码'
})

const phoneCodeText = computed(() => {
  return phoneCodeCountdown.value > 0 ? `${phoneCodeCountdown.value}s` : '获取验证码'
})

// 发送邮箱验证码
const sendEmailCode = async () => {
  if (!registerForm.email) {
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
  if (!registerForm.phone) {
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

// 处理注册
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  try {
    await registerFormRef.value.validate()
    
    registering.value = true
    
    // 这里应该调用注册 API
    const registerData = {
      username: registerForm.username,
      email: registerForm.email,
      phone: registerForm.phone,
      password: registerForm.password,
      emailCode: registerForm.emailCode,
      phoneCode: registerForm.phoneCode,
      inviteCode: registerForm.inviteCode
    }
    
    await userStore.register(registerData)
    
    ElMessage.success('注册成功！')
    
    // 跳转到登录页面
    router.push('/login?message=register-success')
    
  } catch (error: any) {
    ElMessage.error(error.message || '注册失败，请稍后重试')
  } finally {
    registering.value = false
  }
}

// 显示用户协议
const showTerms = () => {
  termsDialogVisible.value = true
}

// 显示隐私政策
const showPrivacy = () => {
  privacyDialogVisible.value = true
}

// 同意用户协议
const acceptTerms = () => {
  registerForm.agreement = true
  termsDialogVisible.value = false
}

// 同意隐私政策
const acceptPrivacy = () => {
  registerForm.agreement = true
  privacyDialogVisible.value = false
}

// 监听密码变化，重新验证确认密码
watch(
  () => registerForm.password,
  () => {
    if (registerForm.confirmPassword) {
      registerFormRef.value?.validateField('confirmPassword')
    }
  }
)
</script>

<style lang="scss" scoped>
.register-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 400px;
  margin: 0 auto;
}

.register-form {
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

.register-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
}

.form-footer {
  text-align: center;
  margin-top: 24px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
  
  .login-link {
    color: var(--el-color-primary);
    text-decoration: none;
    margin-left: 4px;
    
    &:hover {
      text-decoration: underline;
    }
  }
}

.password-strength {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 16px;
  box-shadow: var(--el-box-shadow-light);
  
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

.terms-content,
.privacy-content {
  max-height: 400px;
  overflow-y: auto;
  
  h3 {
    color: var(--el-text-color-primary);
    font-size: 16px;
    margin: 16px 0 8px 0;
    
    &:first-child {
      margin-top: 0;
    }
  }
  
  p {
    color: var(--el-text-color-regular);
    line-height: 1.6;
    margin: 0 0 12px 0;
  }
}

// 响应式设计
@media (max-width: 480px) {
  .register-container {
    gap: 16px;
  }
  
  .register-form {
    padding: 24px 16px;
  }
  
  .form-header {
    margin-bottom: 24px;
    
    h2 {
      font-size: 20px;
    }
  }
  
  .code-input-group {
    flex-direction: column;
    
    .code-btn {
      width: 100%;
    }
  }
  
  .password-strength {
    padding: 12px;
    
    .strength-tips {
      grid-template-columns: 1fr;
    }
  }
}
</style>