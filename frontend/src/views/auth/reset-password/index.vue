<template>
  <div class="reset-password-container">
    <div class="reset-password-form">
      <div class="form-header">
        <h2>重置密码</h2>
        <p>请设置您的新密码</p>
      </div>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        @submit.prevent="handleSubmit"
      >
        <el-form-item prop="newPassword">
          <el-input
            v-model="form.newPassword"
            type="password"
            placeholder="请输入新密码"
            prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>
        
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请确认新密码"
            prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleSubmit"
            class="submit-btn"
          >
            {{ loading ? '重置中...' : '重置密码' }}
          </el-button>
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
      
      <!-- 安全提示 -->
      <div class="security-tips">
        <h4>密码安全建议：</h4>
        <ul>
          <li>使用至少8位字符</li>
          <li>包含大小写字母、数字和特殊字符</li>
          <li>避免使用个人信息（如姓名、生日等）</li>
          <li>不要使用常见密码（如123456、password等）</li>
          <li>定期更换密码以保证账户安全</li>
        </ul>
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import {
  Check, Close, ArrowLeft
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 表单引用
const formRef = ref<FormInstance>()

// 状态
const loading = ref(false)

// 重置令牌（从 URL 参数获取）
const resetToken = ref('')

// 表单数据
const form = reactive({
  newPassword: '',
  confirmPassword: ''
})

// 自定义验证规则
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
  } else if (value !== form.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

// 表单验证规则
const rules: FormRules = {
  newPassword: [{ validator: validateNewPassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

// 密码强度检测
const hasLowerCase = computed(() => /[a-z]/.test(form.newPassword))
const hasUpperCase = computed(() => /[A-Z]/.test(form.newPassword))
const hasNumber = computed(() => /\d/.test(form.newPassword))
const hasSpecialChar = computed(() => /[!@#$%^&*(),.?":{}|<>]/.test(form.newPassword))
const hasMinLength = computed(() => form.newPassword.length >= 8)

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
  return form.newPassword.length > 0
})

// 处理表单提交
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    if (!resetToken.value) {
      ElMessage.error('重置令牌无效，请重新申请密码重置')
      router.push('/forgot-password')
      return
    }
    
    loading.value = true
    
    // 调用密码重置 API
    const resetData = {
      token: resetToken.value,
      newPassword: form.newPassword
    }
    
    await userStore.resetPassword(resetData)
    
    ElMessage.success('密码重置成功，请使用新密码登录')
    
    // 跳转到登录页面
    router.push('/login?message=password-reset-success')
    
  } catch (error: any) {
    if (error.message?.includes('token')) {
      ElMessage.error('重置令牌已过期或无效，请重新申请密码重置')
      router.push('/forgot-password')
    } else {
      ElMessage.error(error.message || '密码重置失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

// 验证重置令牌
const validateResetToken = async () => {
  if (!resetToken.value) {
    ElMessage.error('重置令牌缺失，请重新申请密码重置')
    router.push('/forgot-password')
    return
  }
  
  try {
    // 这里应该调用验证令牌的 API
    // await userStore.validateResetToken(resetToken.value)
    
    // 模拟验证
    await new Promise(resolve => setTimeout(resolve, 500))
    
  } catch (error: any) {
    ElMessage.error('重置令牌无效或已过期，请重新申请密码重置')
    router.push('/forgot-password')
  }
}

// 监听新密码变化，重新验证确认密码
watch(
  () => form.newPassword,
  () => {
    if (form.confirmPassword) {
      formRef.value?.validateField('confirmPassword')
    }
  }
)

// 页面初始化
onMounted(() => {
  // 从 URL 参数获取重置令牌
  resetToken.value = route.query.token as string || ''
  
  // 验证重置令牌
  validateResetToken()
})
</script>

<style lang="scss" scoped>
.reset-password-container {
  max-width: 500px;
  margin: 0 auto;
}

.reset-password-form {
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

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
}

.password-strength {
  margin-bottom: 24px;
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

.security-tips {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--el-fill-color-extra-light);
  border-radius: 6px;
  border-left: 4px solid var(--el-color-primary);
  
  h4 {
    margin: 0 0 12px 0;
    color: var(--el-text-color-primary);
    font-size: 14px;
    font-weight: 600;
  }
  
  ul {
    margin: 0;
    padding-left: 16px;
    
    li {
      color: var(--el-text-color-secondary);
      font-size: 12px;
      line-height: 1.6;
      margin-bottom: 4px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

.form-footer {
  text-align: center;
  
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
  .reset-password-form {
    padding: 24px 16px;
  }
  
  .form-header {
    margin-bottom: 24px;
    
    h2 {
      font-size: 20px;
    }
  }
  
  .password-strength {
    .strength-tips {
      grid-template-columns: 1fr;
    }
  }
}
</style>