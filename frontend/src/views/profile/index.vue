<template>
  <div class="profile-container">
    <!-- 页面头部 -->
    <div class="profile-header">
      <div class="header-content">
        <div class="user-avatar">
          <el-avatar :size="80" :src="userInfo.avatar" icon="el-icon-user-solid" />
          <el-button class="change-avatar-btn" type="text" @click="changeAvatar">
            <el-icon><Camera /></el-icon>
          </el-button>
        </div>
        <div class="user-info">
          <h2>{{ userInfo.name }}</h2>
          <p class="user-title">{{ userInfo.title }}</p>
          <p class="user-email">{{ userInfo.email }}</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="editProfile">
            <el-icon><Edit /></el-icon>
            编辑资料
          </el-button>
        </div>
      </div>
    </div>

    <!-- 主要内容 -->
    <div class="profile-content">
      <el-row :gutter="24">
        <!-- 左侧信息 -->
        <el-col :span="8">
          <!-- 基本信息卡片 -->
          <el-card class="info-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>基本信息</span>
                <el-button type="text" @click="editBasicInfo">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </div>
            </template>
            <div class="info-item">
              <label>用户名：</label>
              <span>{{ userInfo.username }}</span>
            </div>
            <div class="info-item">
              <label>邮箱：</label>
              <span>{{ userInfo.email }}</span>
            </div>
            <div class="info-item">
              <label>手机：</label>
              <span>{{ userInfo.phone || '未设置' }}</span>
            </div>
            <div class="info-item">
              <label>部门：</label>
              <span>{{ userInfo.department || '未设置' }}</span>
            </div>
            <div class="info-item">
              <label>职位：</label>
              <span>{{ userInfo.position || '未设置' }}</span>
            </div>
            <div class="info-item">
              <label>注册时间：</label>
              <span>{{ formatDate(userInfo.createdAt) }}</span>
            </div>
          </el-card>

          <!-- 统计信息卡片 -->
          <el-card class="stats-card" shadow="hover">
            <template #header>
              <span>使用统计</span>
            </template>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-value">{{ userStats.documentsCount }}</div>
                <div class="stat-label">上传文档</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ userStats.questionsCount }}</div>
                <div class="stat-label">提问次数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ userStats.knowledgeCount }}</div>
                <div class="stat-label">知识条目</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ userStats.loginDays }}</div>
                <div class="stat-label">登录天数</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧内容 -->
        <el-col :span="16">
          <!-- 标签页 -->
          <el-tabs v-model="activeTab" class="profile-tabs">
            <!-- 活动记录 -->
            <el-tab-pane label="活动记录" name="activities">
              <div class="activities-list">
                <div v-for="activity in activities" :key="activity.id" class="activity-item">
                  <div class="activity-icon">
                    <el-icon :class="getActivityIconClass(activity.type)">
                      <component :is="getActivityIcon(activity.type)" />
                    </el-icon>
                  </div>
                  <div class="activity-content">
                    <div class="activity-title">{{ activity.title }}</div>
                    <div class="activity-desc">{{ activity.description }}</div>
                    <div class="activity-time">{{ formatDate(activity.createdAt) }}</div>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- 我的文档 -->
            <el-tab-pane label="我的文档" name="documents">
              <div class="documents-list">
                <div v-for="doc in documents" :key="doc.id" class="document-item">
                  <div class="doc-icon">
                    <el-icon><Document /></el-icon>
                  </div>
                  <div class="doc-info">
                    <div class="doc-name">{{ doc.name }}</div>
                    <div class="doc-meta">
                      <span>{{ doc.size }}</span>
                      <span>{{ formatDate(doc.uploadedAt) }}</span>
                    </div>
                  </div>
                  <div class="doc-actions">
                    <el-button type="text" @click="viewDocument(doc)">
                      <el-icon><View /></el-icon>
                    </el-button>
                    <el-button type="text" @click="downloadDocument(doc)">
                      <el-icon><Download /></el-icon>
                    </el-button>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- 设置 -->
            <el-tab-pane label="设置" name="settings">
              <div class="settings-content">
                <!-- 通知设置 -->
                <el-card class="setting-card" shadow="never">
                  <template #header>
                    <span>通知设置</span>
                  </template>
                  <div class="setting-item">
                    <div class="setting-label">
                      <span>邮件通知</span>
                      <p>接收系统邮件通知</p>
                    </div>
                    <el-switch v-model="settings.emailNotification" />
                  </div>
                  <div class="setting-item">
                    <div class="setting-label">
                      <span>浏览器通知</span>
                      <p>接收浏览器推送通知</p>
                    </div>
                    <el-switch v-model="settings.browserNotification" />
                  </div>
                </el-card>

                <!-- 隐私设置 -->
                <el-card class="setting-card" shadow="never">
                  <template #header>
                    <span>隐私设置</span>
                  </template>
                  <div class="setting-item">
                    <div class="setting-label">
                      <span>公开个人资料</span>
                      <p>允许其他用户查看您的基本信息</p>
                    </div>
                    <el-switch v-model="settings.publicProfile" />
                  </div>
                  <div class="setting-item">
                    <div class="setting-label">
                      <span>显示活动状态</span>
                      <p>显示您的在线状态</p>
                    </div>
                    <el-switch v-model="settings.showActivity" />
                  </div>
                </el-card>

                <!-- 安全设置 -->
                <el-card class="setting-card" shadow="never">
                  <template #header>
                    <span>安全设置</span>
                  </template>
                  <div class="setting-item">
                    <div class="setting-label">
                      <span>修改密码</span>
                      <p>定期修改密码以保护账户安全</p>
                    </div>
                    <el-button @click="changePassword">修改密码</el-button>
                  </div>
                  <div class="setting-item">
                    <div class="setting-label">
                      <span>两步验证</span>
                      <p>启用两步验证增强账户安全</p>
                    </div>
                    <el-switch v-model="settings.twoFactorAuth" />
                  </div>
                </el-card>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Camera,
  Edit,
  Document,
  View,
  Download,
  User,
  Message,
  Upload,
  Search
} from '@element-plus/icons-vue'

// 响应式数据
const activeTab = ref('activities')

const userInfo = reactive({
  id: 1,
  name: '张三',
  username: 'zhangsan',
  email: 'zhangsan@example.com',
  phone: '138****8888',
  title: '高级工程师',
  department: '技术部',
  position: '前端开发工程师',
  avatar: '',
  createdAt: '2023-01-15T08:00:00Z'
})

const userStats = reactive({
  documentsCount: 156,
  questionsCount: 89,
  knowledgeCount: 234,
  loginDays: 128
})

const settings = reactive({
  emailNotification: true,
  browserNotification: false,
  publicProfile: true,
  showActivity: true,
  twoFactorAuth: false
})

const activities = ref([
  {
    id: 1,
    type: 'upload',
    title: '上传了文档',
    description: '上传了《Vue3开发指南.pdf》',
    createdAt: '2024-01-15T10:30:00Z'
  },
  {
    id: 2,
    type: 'question',
    title: '提出了问题',
    description: '如何在Vue3中使用Composition API？',
    createdAt: '2024-01-15T09:15:00Z'
  },
  {
    id: 3,
    type: 'knowledge',
    title: '创建了知识条目',
    description: '添加了关于React Hooks的知识点',
    createdAt: '2024-01-14T16:45:00Z'
  }
])

const documents = ref([
  {
    id: 1,
    name: 'Vue3开发指南.pdf',
    size: '2.5MB',
    uploadedAt: '2024-01-15T10:30:00Z'
  },
  {
    id: 2,
    name: 'React最佳实践.docx',
    size: '1.8MB',
    uploadedAt: '2024-01-14T14:20:00Z'
  },
  {
    id: 3,
    name: 'JavaScript高级编程.pdf',
    size: '5.2MB',
    uploadedAt: '2024-01-13T11:10:00Z'
  }
])

// 方法
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const getActivityIcon = (type) => {
  const iconMap = {
    upload: Upload,
    question: Message,
    knowledge: Document,
    search: Search
  }
  return iconMap[type] || Document
}

const getActivityIconClass = (type) => {
  const classMap = {
    upload: 'upload-icon',
    question: 'question-icon',
    knowledge: 'knowledge-icon',
    search: 'search-icon'
  }
  return classMap[type] || 'default-icon'
}

const changeAvatar = () => {
  ElMessage.info('头像修改功能开发中...')
}

const editProfile = () => {
  ElMessage.info('编辑资料功能开发中...')
}

const editBasicInfo = () => {
  ElMessage.info('编辑基本信息功能开发中...')
}

const viewDocument = (doc) => {
  ElMessage.info(`查看文档：${doc.name}`)
}

const downloadDocument = (doc) => {
  ElMessage.info(`下载文档：${doc.name}`)
}

const changePassword = () => {
  ElMessage.info('修改密码功能开发中...')
}

// 生命周期
onMounted(() => {
  // 加载用户数据
  console.log('Profile page mounted')
})
</script>

<style scoped>
.profile-container {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.profile-header {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 24px;
}

.user-avatar {
  position: relative;
}

.change-avatar-btn {
  position: absolute;
  bottom: -5px;
  right: -5px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: white;
  border: 2px solid white;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-info {
  flex: 1;
}

.user-info h2 {
  margin: 0 0 8px 0;
  color: #303133;
}

.user-title {
  color: #606266;
  margin: 0 0 4px 0;
  font-size: 14px;
}

.user-email {
  color: #909399;
  margin: 0;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.profile-content {
  gap: 20px;
}

.info-card,
.stats-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-item {
  display: flex;
  margin-bottom: 12px;
  align-items: center;
}

.info-item label {
  width: 80px;
  color: #606266;
  font-size: 14px;
}

.info-item span {
  color: #303133;
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 6px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.profile-tabs {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.activities-list {
  max-height: 500px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  background: #f0f9ff;
}

.upload-icon {
  color: #10b981;
}

.question-icon {
  color: #f59e0b;
}

.knowledge-icon {
  color: #3b82f6;
}

.search-icon {
  color: #8b5cf6;
}

.activity-content {
  flex: 1;
}

.activity-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.activity-desc {
  color: #606266;
  font-size: 14px;
  margin-bottom: 4px;
}

.activity-time {
  color: #909399;
  font-size: 12px;
}

.documents-list {
  max-height: 500px;
  overflow-y: auto;
}

.document-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.document-item:last-child {
  border-bottom: none;
}

.doc-icon {
  width: 40px;
  height: 40px;
  background: #f0f9ff;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  color: #3b82f6;
}

.doc-info {
  flex: 1;
}

.doc-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.doc-meta {
  display: flex;
  gap: 16px;
  color: #909399;
  font-size: 12px;
}

.doc-actions {
  display: flex;
  gap: 8px;
}

.settings-content {
  max-height: 500px;
  overflow-y: auto;
}

.setting-card {
  margin-bottom: 20px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label span {
  font-weight: 500;
  color: #303133;
  display: block;
  margin-bottom: 4px;
}

.setting-label p {
  color: #909399;
  font-size: 12px;
  margin: 0;
}
</style>