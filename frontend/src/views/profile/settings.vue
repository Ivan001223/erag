<template>
  <div class="profile-settings">
    <div class="settings-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">
          <el-icon><User /></el-icon>
          个人设置
        </h1>
        <p class="page-description">管理您的个人信息、安全设置和偏好配置</p>
      </div>

      <!-- 设置内容 -->
      <div class="settings-content">
        <!-- 左侧导航 -->
        <div class="settings-nav">
          <el-menu
            v-model="activeTab"
            mode="vertical"
            class="settings-menu"
            @select="handleTabChange"
          >
            <el-menu-item index="basic">
              <el-icon><User /></el-icon>
              <span>基本信息</span>
            </el-menu-item>
            <el-menu-item index="security">
              <el-icon><Lock /></el-icon>
              <span>安全设置</span>
            </el-menu-item>
            <el-menu-item index="notification">
              <el-icon><Bell /></el-icon>
              <span>通知设置</span>
            </el-menu-item>
            <el-menu-item index="appearance">
              <el-icon><Monitor /></el-icon>
              <span>外观设置</span>
            </el-menu-item>
            <el-menu-item index="privacy">
              <el-icon><View /></el-icon>
              <span>隐私设置</span>
            </el-menu-item>
          </el-menu>
        </div>

        <!-- 右侧内容 -->
        <div class="settings-main">
          <!-- 基本信息 -->
          <div v-show="activeTab === 'basic'" class="settings-panel">
            <div class="panel-header">
              <h2>基本信息</h2>
              <p>更新您的个人基本信息</p>
            </div>
            
            <el-form
              ref="basicFormRef"
              :model="basicForm"
              :rules="basicRules"
              label-width="100px"
              class="settings-form"
            >
              <!-- 头像上传 -->
              <el-form-item label="头像">
                <div class="avatar-upload">
                  <el-upload
                    class="avatar-uploader"
                    action="/api/upload/avatar"
                    :show-file-list="false"
                    :on-success="handleAvatarSuccess"
                    :before-upload="beforeAvatarUpload"
                  >
                    <img v-if="basicForm.avatar" :src="basicForm.avatar" class="avatar" />
                    <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
                  </el-upload>
                  <div class="avatar-tips">
                    <p>支持 JPG、PNG 格式</p>
                    <p>文件大小不超过 2MB</p>
                  </div>
                </div>
              </el-form-item>
              
              <el-form-item label="用户名" prop="username">
                <el-input v-model="basicForm.username" placeholder="请输入用户名" />
              </el-form-item>
              
              <el-form-item label="真实姓名" prop="realName">
                <el-input v-model="basicForm.realName" placeholder="请输入真实姓名" />
              </el-form-item>
              
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="basicForm.email" placeholder="请输入邮箱地址" />
              </el-form-item>
              
              <el-form-item label="手机号" prop="phone">
                <el-input v-model="basicForm.phone" placeholder="请输入手机号" />
              </el-form-item>
              
              <el-form-item label="部门">
                <el-select v-model="basicForm.department" placeholder="请选择部门" style="width: 100%">
                  <el-option label="技术部" value="tech" />
                  <el-option label="产品部" value="product" />
                  <el-option label="运营部" value="operation" />
                  <el-option label="市场部" value="marketing" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="职位">
                <el-input v-model="basicForm.position" placeholder="请输入职位" />
              </el-form-item>
              
              <el-form-item label="个人简介">
                <el-input
                  v-model="basicForm.bio"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入个人简介"
                  maxlength="200"
                  show-word-limit
                />
              </el-form-item>
              
              <el-form-item>
                <el-button type="primary" @click="saveBasicInfo" :loading="saving">
                  保存更改
                </el-button>
                <el-button @click="resetBasicForm">重置</el-button>
              </el-form-item>
            </el-form>
          </div>

          <!-- 安全设置 -->
          <div v-show="activeTab === 'security'" class="settings-panel">
            <div class="panel-header">
              <h2>安全设置</h2>
              <p>管理您的账户安全</p>
            </div>
            
            <!-- 修改密码 -->
            <div class="security-section">
              <h3>修改密码</h3>
              <el-form
                ref="passwordFormRef"
                :model="passwordForm"
                :rules="passwordRules"
                label-width="120px"
                class="settings-form"
              >
                <el-form-item label="当前密码" prop="currentPassword">
                  <el-input
                    v-model="passwordForm.currentPassword"
                    type="password"
                    placeholder="请输入当前密码"
                    show-password
                  />
                </el-form-item>
                
                <el-form-item label="新密码" prop="newPassword">
                  <el-input
                    v-model="passwordForm.newPassword"
                    type="password"
                    placeholder="请输入新密码"
                    show-password
                  />
                </el-form-item>
                
                <el-form-item label="确认新密码" prop="confirmPassword">
                  <el-input
                    v-model="passwordForm.confirmPassword"
                    type="password"
                    placeholder="请再次输入新密码"
                    show-password
                  />
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="changePassword" :loading="changingPassword">
                    修改密码
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
            
            <!-- 两步验证 -->
            <div class="security-section">
              <h3>两步验证</h3>
              <div class="security-item">
                <div class="security-info">
                  <h4>短信验证</h4>
                  <p>通过短信接收验证码</p>
                </div>
                <el-switch v-model="securitySettings.smsAuth" @change="toggleSmsAuth" />
              </div>
              
              <div class="security-item">
                <div class="security-info">
                  <h4>邮箱验证</h4>
                  <p>通过邮箱接收验证码</p>
                </div>
                <el-switch v-model="securitySettings.emailAuth" @change="toggleEmailAuth" />
              </div>
            </div>
            
            <!-- 登录设备 -->
            <div class="security-section">
              <h3>登录设备</h3>
              <div class="device-list">
                <div v-for="device in loginDevices" :key="device.id" class="device-item">
                  <div class="device-info">
                    <div class="device-name">
                      <el-icon><Monitor /></el-icon>
                      {{ device.name }}
                    </div>
                    <div class="device-details">
                      <span>{{ device.location }}</span>
                      <span>{{ device.lastLogin }}</span>
                    </div>
                  </div>
                  <div class="device-actions">
                    <el-tag v-if="device.current" type="success">当前设备</el-tag>
                    <el-button v-else type="danger" size="small" @click="removeDevice(device.id)">
                      移除
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 通知设置 -->
          <div v-show="activeTab === 'notification'" class="settings-panel">
            <div class="panel-header">
              <h2>通知设置</h2>
              <p>管理您的通知偏好</p>
            </div>
            
            <div class="notification-section">
              <h3>邮箱通知</h3>
              <div class="notification-item">
                <div class="notification-info">
                  <h4>系统通知</h4>
                  <p>接收系统重要通知和更新</p>
                </div>
                <el-switch v-model="notificationSettings.emailSystem" />
              </div>
              
              <div class="notification-item">
                <div class="notification-info">
                  <h4>安全通知</h4>
                  <p>接收账户安全相关通知</p>
                </div>
                <el-switch v-model="notificationSettings.emailSecurity" />
              </div>
              
              <div class="notification-item">
                <div class="notification-info">
                  <h4>营销通知</h4>
                  <p>接收产品更新和营销信息</p>
                </div>
                <el-switch v-model="notificationSettings.emailMarketing" />
              </div>
            </div>
            
            <div class="notification-section">
              <h3>浏览器通知</h3>
              <div class="notification-item">
                <div class="notification-info">
                  <h4>桌面通知</h4>
                  <p>在浏览器中显示桌面通知</p>
                </div>
                <el-switch v-model="notificationSettings.browserNotification" @change="toggleBrowserNotification" />
              </div>
            </div>
            
            <div class="notification-actions">
              <el-button type="primary" @click="saveNotificationSettings" :loading="saving">
                保存设置
              </el-button>
            </div>
          </div>

          <!-- 外观设置 -->
          <div v-show="activeTab === 'appearance'" class="settings-panel">
            <div class="panel-header">
              <h2>外观设置</h2>
              <p>自定义您的界面外观</p>
            </div>
            
            <div class="appearance-section">
              <h3>主题设置</h3>
              <el-radio-group v-model="appearanceSettings.theme" @change="changeTheme">
                <el-radio value="light">浅色主题</el-radio>
                <el-radio value="dark">深色主题</el-radio>
                <el-radio value="auto">跟随系统</el-radio>
              </el-radio-group>
            </div>
            
            <div class="appearance-section">
              <h3>语言设置</h3>
              <el-select v-model="appearanceSettings.language" @change="changeLanguage">
                <el-option label="简体中文" value="zh-CN" />
                <el-option label="English" value="en-US" />
                <el-option label="繁體中文" value="zh-TW" />
              </el-select>
            </div>
            
            <div class="appearance-section">
              <h3>字体大小</h3>
              <el-radio-group v-model="appearanceSettings.fontSize" @change="changeFontSize">
                <el-radio value="small">小</el-radio>
                <el-radio value="medium">中</el-radio>
                <el-radio value="large">大</el-radio>
              </el-radio-group>
            </div>
          </div>

          <!-- 隐私设置 -->
          <div v-show="activeTab === 'privacy'" class="settings-panel">
            <div class="panel-header">
              <h2>隐私设置</h2>
              <p>管理您的隐私和数据设置</p>
            </div>
            
            <div class="privacy-section">
              <h3>个人信息可见性</h3>
              <div class="privacy-item">
                <div class="privacy-info">
                  <h4>显示真实姓名</h4>
                  <p>其他用户可以看到您的真实姓名</p>
                </div>
                <el-switch v-model="privacySettings.showRealName" />
              </div>
              
              <div class="privacy-item">
                <div class="privacy-info">
                  <h4>显示邮箱地址</h4>
                  <p>其他用户可以看到您的邮箱地址</p>
                </div>
                <el-switch v-model="privacySettings.showEmail" />
              </div>
              
              <div class="privacy-item">
                <div class="privacy-info">
                  <h4>显示在线状态</h4>
                  <p>其他用户可以看到您的在线状态</p>
                </div>
                <el-switch v-model="privacySettings.showOnlineStatus" />
              </div>
            </div>
            
            <div class="privacy-section">
              <h3>数据管理</h3>
              <div class="data-actions">
                <el-button @click="exportData">导出个人数据</el-button>
                <el-button type="danger" @click="deleteAccount">删除账户</el-button>
              </div>
            </div>
            
            <div class="privacy-actions">
              <el-button type="primary" @click="savePrivacySettings" :loading="saving">
                保存设置
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormRules } from 'element-plus'
import {
  User,
  Lock,
  Bell,
  Monitor,
  View,
  Plus
} from '@element-plus/icons-vue'

// 当前激活的标签页
const activeTab = ref('basic')

// 保存状态
const saving = ref(false)
const changingPassword = ref(false)

// 基本信息表单
const basicForm = reactive({
  avatar: '',
  username: '',
  realName: '',
  email: '',
  phone: '',
  department: '',
  position: '',
  bio: ''
})

// 基本信息验证规则
const basicRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  realName: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

// 密码修改表单
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 密码验证规则
const passwordRules: FormRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string, callback: (error?: Error) => void) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ]
}

// 安全设置
const securitySettings = reactive({
  smsAuth: false,
  emailAuth: true
})

// 通知设置
const notificationSettings = reactive({
  emailSystem: true,
  emailSecurity: true,
  emailMarketing: false,
  browserNotification: false
})

// 外观设置
const appearanceSettings = reactive({
  theme: 'light',
  language: 'zh-CN',
  fontSize: 'medium'
})

// 隐私设置
const privacySettings = reactive({
  showRealName: true,
  showEmail: false,
  showOnlineStatus: true
})

// 登录设备列表
const loginDevices = ref([
  {
    id: 1,
    name: 'Windows PC - Chrome',
    location: '北京市',
    lastLogin: '2024-01-15 14:30',
    current: true
  },
  {
    id: 2,
    name: 'iPhone - Safari',
    location: '上海市',
    lastLogin: '2024-01-14 09:15',
    current: false
  }
])

// 表单引用
const basicFormRef = ref()
const passwordFormRef = ref()

// 切换标签页
const handleTabChange = (key: string) => {
  activeTab.value = key
}

// 头像上传成功
const handleAvatarSuccess = (response: any) => {
  basicForm.avatar = response.data.url
  ElMessage.success('头像上传成功')
}

// 头像上传前验证
const beforeAvatarUpload = (file: File) => {
  const isJPG = file.type === 'image/jpeg' || file.type === 'image/png'
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isJPG) {
    ElMessage.error('头像图片只能是 JPG/PNG 格式!')
  }
  if (!isLt2M) {
    ElMessage.error('头像图片大小不能超过 2MB!')
  }
  return isJPG && isLt2M
}

// 保存基本信息
const saveBasicInfo = async () => {
  if (!basicFormRef.value) return
  
  try {
    await basicFormRef.value.validate()
    saving.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('基本信息保存成功')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 重置基本信息表单
const resetBasicForm = () => {
  if (basicFormRef.value) {
    basicFormRef.value.resetFields()
  }
}

// 修改密码
const changePassword = async () => {
  if (!passwordFormRef.value) return
  
  try {
    await passwordFormRef.value.validate()
    changingPassword.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('密码修改成功')
    
    // 重置表单
    passwordFormRef.value.resetFields()
  } catch (error) {
    console.error('密码修改失败:', error)
  } finally {
    changingPassword.value = false
  }
}

// 切换短信验证
const toggleSmsAuth = (value: boolean) => {
  ElMessage.success(value ? '短信验证已开启' : '短信验证已关闭')
}

// 切换邮箱验证
const toggleEmailAuth = (value: boolean) => {
  ElMessage.success(value ? '邮箱验证已开启' : '邮箱验证已关闭')
}

// 移除设备
const removeDevice = async (deviceId: number) => {
  try {
    await ElMessageBox.confirm('确定要移除此设备吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const index = loginDevices.value.findIndex(device => device.id === deviceId)
    if (index > -1) {
      loginDevices.value.splice(index, 1)
      ElMessage.success('设备已移除')
    }
  } catch {
    // 用户取消
  }
}

// 切换浏览器通知
const toggleBrowserNotification = (value: boolean) => {
  if (value) {
    if ('Notification' in window) {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          ElMessage.success('浏览器通知已开启')
        } else {
          notificationSettings.browserNotification = false
          ElMessage.warning('请在浏览器设置中允许通知权限')
        }
      })
    } else {
      notificationSettings.browserNotification = false
      ElMessage.error('您的浏览器不支持通知功能')
    }
  } else {
    ElMessage.success('浏览器通知已关闭')
  }
}

// 保存通知设置
const saveNotificationSettings = async () => {
  saving.value = true
  
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('通知设置保存成功')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 切换主题
const changeTheme = (theme: string) => {
  ElMessage.success(`已切换到${theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '自动'}主题`)
}

// 切换语言
const changeLanguage = (language: string) => {
  const languageMap: Record<string, string> = {
    'zh-CN': '简体中文',
    'en-US': 'English',
    'zh-TW': '繁體中文'
  }
  ElMessage.success(`语言已切换为${languageMap[language]}`)
}

// 切换字体大小
const changeFontSize = (fontSize: string) => {
  const sizeMap: Record<string, string> = {
    small: '小',
    medium: '中',
    large: '大'
  }
  ElMessage.success(`字体大小已设置为${sizeMap[fontSize]}`)
}

// 保存隐私设置
const savePrivacySettings = async () => {
  saving.value = true
  
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('隐私设置保存成功')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 导出个人数据
const exportData = async () => {
  try {
    await ElMessageBox.confirm('确定要导出您的个人数据吗？', '导出数据', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })
    
    ElMessage.success('数据导出请求已提交，我们将在24小时内发送到您的邮箱')
  } catch {
    // 用户取消
  }
}

// 删除账户
const deleteAccount = async () => {
  try {
    await ElMessageBox.confirm(
      '删除账户将永久删除您的所有数据，此操作不可恢复。确定要继续吗？',
      '删除账户',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    ElMessage.success('账户删除请求已提交，我们将在7天内处理您的请求')
  } catch {
    // 用户取消
  }
}

// 初始化数据
const initData = () => {
  // 模拟加载用户数据
  Object.assign(basicForm, {
    avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    username: 'john_doe',
    realName: '张三',
    email: 'john@example.com',
    phone: '13800138000',
    department: 'tech',
    position: '前端工程师',
    bio: '热爱技术，专注于前端开发和用户体验设计。'
  })
}

onMounted(() => {
  initData()
})
</script>

<style scoped lang="scss">
.profile-settings {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.settings-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
  
  .page-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 28px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 10px 0;
  }
  
  .page-description {
    color: #606266;
    font-size: 14px;
    margin: 0;
  }
}

.settings-content {
  display: flex;
  gap: 30px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.settings-nav {
  width: 240px;
  background: #fafbfc;
  border-right: 1px solid #e4e7ed;
  
  .settings-menu {
    border: none;
    background: transparent;
    
    .el-menu-item {
      height: 50px;
      line-height: 50px;
      margin: 0;
      border-radius: 0;
      
      &:hover {
        background-color: #ecf5ff;
        color: #409eff;
      }
      
      &.is-active {
        background-color: #409eff;
        color: white;
        
        &::after {
          display: none;
        }
      }
    }
  }
}

.settings-main {
  flex: 1;
  padding: 30px;
}

.settings-panel {
  .panel-header {
    margin-bottom: 30px;
    padding-bottom: 15px;
    border-bottom: 1px solid #e4e7ed;
    
    h2 {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 5px 0;
    }
    
    p {
      color: #606266;
      font-size: 14px;
      margin: 0;
    }
  }
}

.settings-form {
  max-width: 500px;
  
  .el-form-item {
    margin-bottom: 25px;
  }
}

.avatar-upload {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  
  .avatar-uploader {
    :deep(.el-upload) {
      border: 1px dashed #d9d9d9;
      border-radius: 6px;
      cursor: pointer;
      position: relative;
      overflow: hidden;
      transition: 0.2s;
      
      &:hover {
        border-color: #409eff;
      }
    }
  }
  
  .avatar {
    width: 80px;
    height: 80px;
    display: block;
    border-radius: 6px;
  }
  
  .avatar-uploader-icon {
    font-size: 28px;
    color: #8c939d;
    width: 80px;
    height: 80px;
    text-align: center;
    line-height: 80px;
  }
  
  .avatar-tips {
    font-size: 12px;
    color: #909399;
    
    p {
      margin: 0 0 5px 0;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

.security-section {
  margin-bottom: 40px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 20px 0;
  }
}

.security-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 0;
  border-bottom: 1px solid #f0f0f0;
  
  &:last-child {
    border-bottom: none;
  }
  
  .security-info {
    h4 {
      font-size: 14px;
      font-weight: 500;
      color: #303133;
      margin: 0 0 5px 0;
    }
    
    p {
      font-size: 12px;
      color: #909399;
      margin: 0;
    }
  }
}

.device-list {
  .device-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    margin-bottom: 10px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .device-info {
      .device-name {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        color: #303133;
        margin-bottom: 5px;
      }
      
      .device-details {
        font-size: 12px;
        color: #909399;
        
        span {
          margin-right: 15px;
        }
      }
    }
  }
}

.notification-section {
  margin-bottom: 30px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 20px 0;
  }
}

.notification-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 0;
  border-bottom: 1px solid #f0f0f0;
  
  &:last-child {
    border-bottom: none;
  }
  
  .notification-info {
    h4 {
      font-size: 14px;
      font-weight: 500;
      color: #303133;
      margin: 0 0 5px 0;
    }
    
    p {
      font-size: 12px;
      color: #909399;
      margin: 0;
    }
  }
}

.notification-actions {
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.appearance-section {
  margin-bottom: 30px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 15px 0;
  }
  
  .el-radio-group {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .el-select {
    width: 200px;
  }
}

.privacy-section {
  margin-bottom: 30px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 20px 0;
  }
}

.privacy-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 0;
  border-bottom: 1px solid #f0f0f0;
  
  &:last-child {
    border-bottom: none;
  }
  
  .privacy-info {
    h4 {
      font-size: 14px;
      font-weight: 500;
      color: #303133;
      margin: 0 0 5px 0;
    }
    
    p {
      font-size: 12px;
      color: #909399;
      margin: 0;
    }
  }
}

.data-actions {
  display: flex;
  gap: 15px;
}

.privacy-actions {
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

// 响应式设计
@media (max-width: 768px) {
  .settings-content {
    flex-direction: column;
  }
  
  .settings-nav {
    width: 100%;
    
    .settings-menu {
      display: flex;
      overflow-x: auto;
      
      .el-menu-item {
        white-space: nowrap;
        min-width: 120px;
      }
    }
  }
  
  .settings-main {
    padding: 20px;
  }
  
  .avatar-upload {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .data-actions {
    flex-direction: column;
    
    .el-button {
      width: 100%;
    }
  }
}
</style>