<template>
  <div class="login-page">
    <div class="login-form">
      <div class="form-header">
        <h2 class="form-title">欢迎回来</h2>
        <p class="form-subtitle">请登录您的账户</p>
      </div>
      
      <el-form 
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form-content"
        size="large"
        @keyup.enter="handleLogin"
      >
        <!-- 用户名/邮箱 -->
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名或邮箱"
            prefix-icon="User"
            clearable
          />
        </el-form-item>
        
        <!-- 密码 -->
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>
        
        <!-- 验证码 -->
        <el-form-item prop="captcha" v-if="showCaptcha">
          <div class="captcha-container">
            <el-input
              v-model="loginForm.captcha"
              placeholder="请输入验证码"
              prefix-icon="Picture"
              clearable
              style="flex: 1"
            />
            <div class="captcha-image" @click="refreshCaptcha">
              <img :src="captchaUrl" alt="验证码" />
            </div>
          </div>
        </el-form-item>
        
        <!-- 记住我和忘记密码 -->
        <div class="form-options">
          <el-checkbox v-model="loginForm.rememberMe">
            记住我
          </el-checkbox>
          <el-button type="primary" link @click="goToForgotPassword">
            忘记密码？
          </el-button>
        </div>
        
        <!-- 登录按钮 -->
        <el-form-item>
          <el-button 
            type="primary" 
            class="login-button"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
        
        <!-- 第三方登录 -->
        <div class="social-login" v-if="enableSocialLogin">
          <div class="divider">
            <span>或者使用以下方式登录</span>
          </div>
          
          <div class="social-buttons">
            <el-button 
              v-for="provider in socialProviders" 
              :key="provider.name"
              class="social-button"
              @click="handleSocialLogin(provider)"
            >
              <el-icon class="social-icon">
                <component :is="provider.icon" />
              </el-icon>
              {{ provider.label }}
            </el-button>
          </div>
        </div>
        
        <!-- 注册链接 -->
        <div class="register-link">
          <span>还没有账户？</span>
          <el-button type="primary" link @click="goToRegister">
            立即注册
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElNotification, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Picture } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import type { LoginForm } from '@/types/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()

// 表单引用
const loginFormRef = ref<FormInstance>()

// 加载状态
const loading = ref(false)

// 是否显示验证码
const showCaptcha = ref(false)

// 验证码URL
const captchaUrl = ref('')

// 是否启用第三方登录
const enableSocialLogin = ref(true)

// 登录表单数据
const loginForm = reactive<LoginForm>({
  username: '',
  password: '',
  captcha: '',
  rememberMe: false
})

// 表单验证规则
const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  captcha: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '验证码长度为 4 位', trigger: 'blur' }
  ]
}

// 第三方登录提供商
const socialProviders = ref([
  {
    name: 'github',
    label: 'GitHub',
    icon: 'Github'
  },
  {
    name: 'google',
    label: 'Google',
    icon: 'Google'
  },
  {
    name: 'wechat',
    label: '微信',
    icon: 'Wechat'
  }
])

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    const valid = await loginFormRef.value.validate()
    if (!valid) return
    
    loading.value = true
    
    // 调用登录API
    await userStore.login(loginForm)
    
    ElMessage.success('登录成功')
    
    // 跳转到目标页面或首页
    const redirect = route.query.redirect as string || '/dashboard'
    router.push(redirect)
    
  } catch (error: any) {
    console.error('Login error:', error)
    
    // 根据错误类型显示不同消息
    if (error.code === 'INVALID_CAPTCHA') {
      showCaptcha.value = true
      refreshCaptcha()
      ElMessage.error('验证码错误，请重新输入')
    } else if (error.code === 'ACCOUNT_LOCKED') {
      ElMessage.error('账户已被锁定，请联系管理员')
    } else if (error.code === 'INVALID_CREDENTIALS') {
      ElMessage.error('用户名或密码错误')
    } else {
      ElMessage.error(error.message || '登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

// 刷新验证码
const refreshCaptcha = () => {
  captchaUrl.value = `/api/auth/captcha?t=${Date.now()}`
}

// 第三方登录
const handleSocialLogin = (provider: any) => {
  ElMessage.info(`${provider.label} 登录功能开发中...`)
  // 这里实现第三方登录逻辑
}

// 跳转到注册页面
const goToRegister = () => {
  router.push('/register')
}

// 跳转到忘记密码页面
const goToForgotPassword = () => {
  router.push('/forgot-password')
}

// 组件挂载时的初始化
onMounted(() => {
  // 如果已经登录，直接跳转
  if (userStore.isLoggedIn) {
    const redirect = route.query.redirect as string || '/dashboard'
    router.push(redirect)
    return
  }
  
  // 检查是否需要显示验证码
  checkCaptchaRequired()
  
  // 显示欢迎消息
  if (route.query.message === 'logout') {
    ElNotification({
      title: '退出成功',
      message: '您已安全退出系统',
      type: 'success',
      duration: 3000
    })
  }
})

// 检查是否需要验证码
const checkCaptchaRequired = async () => {
  try {
    // 这里可以调用API检查是否需要验证码
    // const response = await api.checkCaptchaRequired()
    // showCaptcha.value = response.required
    
    if (showCaptcha.value) {
      refreshCaptcha()
    }
  } catch (error) {
    console.error('Check captcha error:', error)
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-form {
  width: 100%;
  max-width: 400px;
  padding: 0;
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
  
  .form-title {
    font-size: 28px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin: 0 0 8px 0;
  }
  
  .form-subtitle {
    font-size: 16px;
    color: var(--el-text-color-regular);
    margin: 0;
  }
}

.login-form-content {
  .captcha-container {
    display: flex;
    gap: 12px;
    align-items: center;
    
    .captcha-image {
      width: 100px;
      height: 40px;
      border: 1px solid var(--el-border-color);
      border-radius: 4px;
      cursor: pointer;
      overflow: hidden;
      
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      
      &:hover {
        border-color: var(--el-color-primary);
      }
    }
  }
  
  .form-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }
  
  .login-button {
    width: 100%;
    height: 44px;
    font-size: 16px;
    font-weight: 500;
  }
}

.social-login {
  margin-top: 24px;
  
  .divider {
    position: relative;
    text-align: center;
    margin: 24px 0;
    
    &::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 0;
      right: 0;
      height: 1px;
      background: var(--el-border-color-light);
    }
    
    span {
      background: var(--el-bg-color);
      padding: 0 16px;
      font-size: 14px;
      color: var(--el-text-color-regular);
    }
  }
  
  .social-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
    
    .social-button {
      width: 100%;
      height: 40px;
      border: 1px solid var(--el-border-color);
      background: var(--el-bg-color);
      color: var(--el-text-color-primary);
      
      .social-icon {
        margin-right: 8px;
      }
      
      &:hover {
        border-color: var(--el-color-primary);
        color: var(--el-color-primary);
      }
    }
  }
}

.register-link {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

// 响应式设计
@media (max-width: 480px) {
  .login-form {
    padding: 0 16px;
  }
  
  .form-header {
    .form-title {
      font-size: 24px;
    }
    
    .form-subtitle {
      font-size: 14px;
    }
  }
  
  .social-buttons {
    .social-button {
      height: 36px;
      font-size: 14px;
    }
  }
}
</style>