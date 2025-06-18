import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { userApi } from '@/api/user'
import type { User, LoginForm, RegisterForm, UserProfile } from '@/types/user'
import { useRouter } from 'vue-router'

// 用户权限枚举
export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  VIEWER = 'viewer'
}

// 用户状态接口
interface UserState {
  user: User | null
  token: string | null
  refreshToken: string | null
  permissions: string[]
  isLoggedIn: boolean
  loginLoading: boolean
  registerLoading: boolean
  profileLoading: boolean
  lastLoginTime: string | null
  sessionExpiry: number | null
}

export const useUserStore = defineStore('user', () => {
  const router = useRouter()
  
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const permissions = ref<string[]>([])
  const isLoggedIn = ref(false)
  const loginLoading = ref(false)
  const registerLoading = ref(false)
  const profileLoading = ref(false)
  const lastLoginTime = ref<string | null>(null)
  const sessionExpiry = ref<number | null>(null)
  const routesInitialized = ref(false)
  
  // 计算属性
  const isAdmin = computed(() => user.value?.role === UserRole.ADMIN)
  const isUser = computed(() => user.value?.role === UserRole.USER)
  const isViewer = computed(() => user.value?.role === UserRole.VIEWER)
  const roles = computed(() => user.value?.role ? [user.value.role] : [])
  
  const hasPermission = computed(() => {
    return (permission: string) => {
      if (isAdmin.value) return true
      return permissions.value.includes(permission)
    }
  })
  
  const hasAnyPermission = computed(() => {
    return (perms: string[]) => {
      if (isAdmin.value) return true
      return perms.some(perm => permissions.value.includes(perm))
    }
  })
  
  const hasAllPermissions = computed(() => {
    return (perms: string[]) => {
      if (isAdmin.value) return true
      return perms.every(perm => permissions.value.includes(perm))
    }
  })
  
  const userDisplayName = computed(() => {
    if (!user.value) return ''
    return user.value.nickname || user.value.username || user.value.email
  })
  
  const userInfo = computed(() => user.value)
  
  const isSessionExpired = computed(() => {
    if (!sessionExpiry.value) return false
    return Date.now() > sessionExpiry.value
  })
  
  // 动作
  const login = async (loginForm: LoginForm) => {
    try {
      loginLoading.value = true
      
      const response = await userApi.login(loginForm)
      
      if (response.success) {
        // 设置用户信息
        user.value = response.data.user
        token.value = response.data.token
        refreshToken.value = response.data.refreshToken
        permissions.value = response.data.permissions || []
        isLoggedIn.value = true
        lastLoginTime.value = new Date().toISOString()
        sessionExpiry.value = Date.now() + (response.data.expiresIn * 1000)
        
        // 保存到本地存储
        saveToStorage()
        
        // 设置 API 默认 token
        setApiToken(token.value)
        
        ElMessage.success('登录成功')
        ElNotification({
          title: '欢迎回来',
          message: `欢迎 ${userDisplayName.value}`,
          type: 'success',
          duration: 3000
        })
        
        // 跳转到首页或之前访问的页面
        const redirect = router.currentRoute.value.query.redirect as string
        await router.push(redirect || '/dashboard')
        
        return true
      } else {
        ElMessage.error(response.message || '登录失败')
        return false
      }
    } catch (error: any) {
      console.error('登录失败:', error)
      ElMessage.error(error.message || '登录失败，请稍后重试')
      return false
    } finally {
      loginLoading.value = false
    }
  }
  
  const register = async (registerForm: RegisterForm) => {
    try {
      registerLoading.value = true
      
      const response = await userApi.register(registerForm)
      
      if (response.success) {
        ElMessage.success('注册成功，请登录')
        ElNotification({
          title: '注册成功',
          message: '账号已创建，请使用新账号登录',
          type: 'success',
          duration: 5000
        })
        
        // 跳转到登录页
        await router.push('/login')
        
        return true
      } else {
        ElMessage.error(response.message || '注册失败')
        return false
      }
    } catch (error: any) {
      console.error('注册失败:', error)
      ElMessage.error(error.message || '注册失败，请稍后重试')
      return false
    } finally {
      registerLoading.value = false
    }
  }
  
  const logout = async (showMessage = true) => {
    try {
      // 调用登出 API
      if (token.value) {
        await userApi.logout()
      }
    } catch (error) {
      console.error('登出 API 调用失败:', error)
    } finally {
      // 清除本地状态
      clearUserState()
      
      if (showMessage) {
        ElMessage.success('已安全退出')
      }
      
      // 跳转到登录页
      await router.push('/login')
    }
  }
  
  const refreshUserToken = async () => {
    try {
      if (!refreshToken.value) {
        throw new Error('没有刷新令牌')
      }
      
      const response = await userApi.refreshToken(refreshToken.value)
      
      if (response.success) {
        token.value = response.data.token
        refreshToken.value = response.data.refreshToken
        sessionExpiry.value = Date.now() + (response.data.expiresIn * 1000)
        
        // 更新存储
        saveToStorage()
        
        // 更新 API token
        setApiToken(token.value)
        
        return true
      } else {
        throw new Error(response.message || '刷新令牌失败')
      }
    } catch (error: any) {
      console.error('刷新令牌失败:', error)
      
      // 刷新失败，强制登出
      await logout(false)
      
      ElMessage.warning('登录已过期，请重新登录')
      return false
    }
  }
  
  const getUserProfile = async () => {
    try {
      profileLoading.value = true
      
      const response = await userApi.getUserInfo()
      
      if (response.success) {
        user.value = { ...user.value, ...response.data }
        saveToStorage()
        return response.data
      } else {
        throw new Error(response.message || '获取用户信息失败')
      }
    } catch (error: any) {
      console.error('获取用户信息失败:', error)
      ElMessage.error(error.message || '获取用户信息失败')
      return null
    } finally {
      profileLoading.value = false
    }
  }
  
  const updateProfile = async (profileData: Partial<UserProfile>) => {
    try {
      profileLoading.value = true
      
      const response = await userApi.updateUserInfo(profileData)
      
      if (response.success) {
        user.value = { ...user.value, ...response.data }
        saveToStorage()
        
        ElMessage.success('个人信息更新成功')
        return true
      } else {
        ElMessage.error(response.message || '更新失败')
        return false
      }
    } catch (error: any) {
      console.error('更新个人信息失败:', error)
      ElMessage.error(error.message || '更新失败，请稍后重试')
      return false
    } finally {
      profileLoading.value = false
    }
  }
  
  const changePassword = async (oldPassword: string, newPassword: string, confirmPassword: string) => {
    try {
      const response = await userApi.changePassword({
        oldPassword,
        newPassword,
        confirmPassword
      })
      
      if (response.success) {
        ElMessage.success('密码修改成功，请重新登录')
        
        // 密码修改后强制重新登录
        await logout(false)
        
        return true
      } else {
        ElMessage.error(response.message || '密码修改失败')
        return false
      }
    } catch (error: any) {
      console.error('密码修改失败:', error)
      ElMessage.error(error.message || '密码修改失败，请稍后重试')
      return false
    }
  }
  
  const checkAuthStatus = async () => {
    try {
      // 检查本地存储的登录状态
      loadFromStorage()
      
      if (!token.value || !user.value) {
        return false
      }
      
      // 检查会话是否过期
      if (isSessionExpired.value) {
        // 尝试刷新令牌
        const refreshed = await refreshUserToken()
        if (!refreshed) {
          return false
        }
      }
      
      // 验证令牌有效性
      const response = await userApi.validateToken()
      
      if (response.success) {
        // 更新用户信息
        // Assuming response.data has a more complex structure than inferred
        const responseData = response.data as any; 
        if (responseData.user) {
          user.value = responseData.user
          permissions.value = responseData.permissions || []
          saveToStorage()
        }
        
        isLoggedIn.value = true
        setApiToken(token.value)
        
        return true
      } else {
        // 令牌无效，清除状态
        clearUserState()
        return false
      }
    } catch (error) {
      console.error('检查认证状态失败:', error)
      clearUserState()
      return false
    }
  }
  
  const clearUserState = () => {
    user.value = null
    token.value = null
    refreshToken.value = null
    permissions.value = []
    isLoggedIn.value = false
    lastLoginTime.value = null
    sessionExpiry.value = null
    routesInitialized.value = false
    
    // 清除本地存储
    clearStorage()
    
    // 清除 API token
    setApiToken(null)
  }
  
  const saveToStorage = () => {
    try {
      const userData = {
        user: user.value,
        token: token.value,
        refreshToken: refreshToken.value,
        permissions: permissions.value,
        lastLoginTime: lastLoginTime.value,
        sessionExpiry: sessionExpiry.value
      }
      
      localStorage.setItem('user-data', JSON.stringify(userData))
    } catch (error) {
      console.error('保存用户数据失败:', error)
    }
  }
  
  const loadFromStorage = () => {
    try {
      const userData = localStorage.getItem('user-data')
      if (userData) {
        const parsed = JSON.parse(userData)
        
        user.value = parsed.user
        token.value = parsed.token
        refreshToken.value = parsed.refreshToken
        permissions.value = parsed.permissions || []
        lastLoginTime.value = parsed.lastLoginTime
        sessionExpiry.value = parsed.sessionExpiry
        
        if (token.value && user.value) {
          isLoggedIn.value = true
        }
      }
    } catch (error) {
      console.error('加载用户数据失败:', error)
      clearStorage()
    }
  }
  
  const clearStorage = () => {
    try {
      localStorage.removeItem('user-data')
    } catch (error) {
      console.error('清除用户数据失败:', error)
    }
  }
  
  const setApiToken = (newToken: string | null) => {
    // 这里应该设置 axios 的默认 Authorization header
    // 具体实现在 api/request.ts 中
    if (newToken) {
      // axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    } else {
      // delete axios.defaults.headers.common['Authorization']
    }
  }
  
  // 初始化路由
  const initializeRoutes = async () => {
    try {
      // 这里可以根据用户权限动态加载路由
      // 目前先简单标记为已初始化
      routesInitialized.value = true
    } catch (error) {
      console.error('路由初始化失败:', error)
      throw error
    }
  }
  
  // 初始化时加载用户数据
  loadFromStorage()
  
  // 别名方法，用于兼容性
  const getUserInfo = getUserProfile
  const refreshUserInfo = async () => {
    try {
      const authValid = await checkAuthStatus()
      if (authValid) {
        return await getUserProfile()
      }
      return null
    } catch (error) {
      console.error('刷新用户信息失败:', error)
      return null
    }
  }

  return {
    // 状态
    user,
    token,
    refreshToken,
    permissions,
    isLoggedIn,
    loginLoading,
    registerLoading,
    profileLoading,
    lastLoginTime,
    sessionExpiry,
    routesInitialized,
    
    // 计算属性
    isAdmin,
    isUser,
    isViewer,
    roles,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    userDisplayName,
    userInfo,
    isSessionExpired,
    
    // 动作
    login,
    register,
    logout,
    refreshUserToken,
    getUserProfile,
    getUserInfo,
    refreshUserInfo,
    updateProfile,
    changePassword,
    checkAuthStatus,
    clearUserState,
    saveToStorage,
    loadFromStorage,
    initializeRoutes
  }
})