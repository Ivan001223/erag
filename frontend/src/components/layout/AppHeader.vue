<template>
  <div class="app-header">
    <!-- 左侧区域 -->
    <div class="header-left">
      <!-- 折叠按钮 -->
      <el-button 
        class="collapse-btn"
        @click="toggleSidebar"
        circle
      >
        <el-icon>
          <Expand v-if="sidebarCollapsed" />
          <Fold v-else />
        </el-icon>
      </el-button>
      
      <!-- 搜索框 -->
      <div class="search-container">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索知识、文档、实体..."
          prefix-icon="Search"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @focus="showSearchSuggestions = true"
          @blur="hideSearchSuggestions"
        />
        
        <!-- 搜索建议 -->
        <div 
          v-show="showSearchSuggestions && searchSuggestions.length > 0"
          class="search-suggestions"
        >
          <div 
            v-for="suggestion in searchSuggestions" 
            :key="suggestion.id"
            class="suggestion-item"
            @click="selectSuggestion(suggestion)"
          >
            <el-icon class="suggestion-icon">
              <component :is="suggestion.icon" />
            </el-icon>
            <div class="suggestion-content">
              <div class="suggestion-title">{{ suggestion.title }}</div>
              <div class="suggestion-type">{{ suggestion.type }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 右侧区域 -->
    <div class="header-right">
      <!-- 快捷操作 -->
      <div class="quick-actions">
        <!-- 全屏切换 -->
        <el-tooltip content="全屏">
          <el-button 
            class="action-btn"
            @click="toggleFullscreen"
            circle
          >
            <el-icon>
              <FullScreen v-if="!isFullscreen" />
              <Aim v-else />
            </el-icon>
          </el-button>
        </el-tooltip>
        
        <!-- 主题切换 -->
        <el-tooltip content="切换主题">
          <el-button 
            class="action-btn"
            @click="toggleTheme"
            circle
          >
            <el-icon>
              <Sunny v-if="isDark" />
              <Moon v-else />
            </el-icon>
          </el-button>
        </el-tooltip>
        
        <!-- 语言切换 -->
        <el-dropdown @command="changeLanguage">
          <el-button class="action-btn" circle>
            <el-icon><Setting /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="zh-CN" :disabled="currentLang === 'zh-CN'">
                <span class="lang-item">
                  <span class="lang-flag">🇨🇳</span>
                  <span>简体中文</span>
                </span>
              </el-dropdown-item>
              <el-dropdown-item command="en-US" :disabled="currentLang === 'en-US'">
                <span class="lang-item">
                  <span class="lang-flag">🇺🇸</span>
                  <span>English</span>
                </span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      
      <!-- 通知中心 -->
      <el-dropdown class="notification-dropdown">
        <el-badge :value="unreadCount" :hidden="unreadCount === 0">
          <el-button class="action-btn" circle>
            <el-icon><Bell /></el-icon>
          </el-button>
        </el-badge>
        <template #dropdown>
          <el-dropdown-menu class="notification-menu">
            <div class="notification-header">
              <span>通知中心</span>
              <el-button type="primary" link size="small" @click="markAllAsRead">
                全部已读
              </el-button>
            </div>
            
            <el-scrollbar max-height="300px">
              <div class="notification-list">
                <div 
                  v-for="notification in notifications" 
                  :key="notification.id"
                  class="notification-item"
                  :class="{ 'unread': !notification.read }"
                  @click="handleNotificationClick(notification)"
                >
                  <div class="notification-icon" :class="notification.type">
                    <el-icon>
                      <component :is="notification.icon" />
                    </el-icon>
                  </div>
                  <div class="notification-content">
                    <div class="notification-title">{{ notification.title }}</div>
                    <div class="notification-message">{{ notification.message }}</div>
                    <div class="notification-time">{{ formatTime(notification.createdAt) }}</div>
                  </div>
                </div>
              </div>
            </el-scrollbar>
            
            <div class="notification-footer">
              <el-button type="primary" link @click="viewAllNotifications">
                查看全部通知
              </el-button>
            </div>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      
      <!-- 用户菜单 -->
      <el-dropdown class="user-dropdown" @command="handleUserCommand">
        <div class="user-info">
          <el-avatar :size="32" :src="userInfo.avatar">
            <el-icon><User /></el-icon>
          </el-avatar>
          <span class="username">{{ userInfo?.nickname || userInfo?.username }}</span>
          <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人资料
            </el-dropdown-item>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              账户设置
            </el-dropdown-item>
            <el-dropdown-item command="help">
              <el-icon><QuestionFilled /></el-icon>
              帮助中心
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Expand, Fold, Search, FullScreen, Aim, Sunny, Moon, Bell,
  User, ArrowDown, Setting, QuestionFilled, SwitchButton,
  Document, Share, InfoFilled, WarningFilled, SuccessFilled
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface Props {
  sidebarCollapsed: boolean
}

interface Emits {
  (e: 'update:sidebarCollapsed', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

// 搜索相关
const searchKeyword = ref('')
const showSearchSuggestions = ref(false)
const searchSuggestions = ref([
  {
    id: '1',
    title: '人工智能技术',
    type: '实体',
    icon: 'Document'
  },
  {
    id: '2',
    title: '企业组织架构',
    type: '图谱',
    icon: 'Share'
  }
])

// 全屏状态
const isFullscreen = ref(false)

// 主题状态
const isDark = computed(() => appStore.isDark)

// 当前语言
const currentLang = computed(() => appStore.language)

// 用户信息
const userInfo = computed(() => userStore.userInfo)

// 通知相关
const notifications = ref([
  {
    id: '1',
    type: 'info',
    icon: 'InfoFilled',
    title: '系统更新',
    message: '系统将在今晚进行维护更新',
    read: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 30)
  },
  {
    id: '2',
    type: 'success',
    icon: 'SuccessFilled',
    title: '文档处理完成',
    message: '您上传的文档"AI发展报告.pdf"已处理完成',
    read: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2)
  },
  {
    id: '3',
    type: 'warning',
    icon: 'WarningFilled',
    title: '存储空间不足',
    message: '当前存储空间使用率已达到85%',
    read: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24)
  }
])

// 未读通知数量
const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.read).length
})

// 切换侧边栏
const toggleSidebar = () => {
  emit('update:sidebarCollapsed', !props.sidebarCollapsed)
}

// 搜索处理
const handleSearch = () => {
  if (searchKeyword.value.trim()) {
    router.push({
      path: '/search',
      query: { q: searchKeyword.value }
    })
    showSearchSuggestions.value = false
  }
}

// 选择搜索建议
const selectSuggestion = (suggestion: any) => {
  searchKeyword.value = suggestion.title
  showSearchSuggestions.value = false
  handleSearch()
}

// 隐藏搜索建议（延迟执行以允许点击）
const hideSearchSuggestions = () => {
  setTimeout(() => {
    showSearchSuggestions.value = false
  }, 200)
}

// 切换全屏
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

// 切换主题
const toggleTheme = () => {
  appStore.toggleTheme()
}

// 切换语言
const changeLanguage = (lang: 'zh-CN' | 'en-US') => {
  appStore.setLanguage(lang)
  ElMessage.success('语言切换成功')
}

// 格式化时间
const formatTime = (date: Date) => {
  return formatDistanceToNow(date, { 
    addSuffix: true, 
    locale: zhCN 
  })
}

// 标记所有通知为已读
const markAllAsRead = () => {
  notifications.value.forEach(n => n.read = true)
  ElMessage.success('已标记所有通知为已读')
}

// 处理通知点击
const handleNotificationClick = (notification: any) => {
  notification.read = true
  // 根据通知类型跳转到相应页面
  ElMessage.info('跳转到通知详情页面')
}

// 查看所有通知
const viewAllNotifications = () => {
  router.push('/notifications')
}

// 处理用户菜单命令
const handleUserCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'help':
      router.push('/help')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '确认退出',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        await userStore.logout()
        router.push('/login?message=logout')
        
      } catch (error) {
        // 用户取消退出
      }
      break
  }
}

// 监听全屏状态变化
const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

// 组件挂载时添加事件监听
onMounted(() => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

// 组件卸载时移除事件监听
onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})
</script>

<style lang="scss" scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 16px;
  background: var(--el-bg-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  
  .collapse-btn {
    width: 36px;
    height: 36px;
    background: var(--el-fill-color-light);
    border: 1px solid var(--el-border-color-light);
    
    &:hover {
      background: var(--el-color-primary-light-9);
      border-color: var(--el-color-primary);
      color: var(--el-color-primary);
    }
  }
  
  .search-container {
    position: relative;
    max-width: 400px;
    flex: 1;
    
    .search-input {
      width: 100%;
    }
    
    .search-suggestions {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: var(--el-bg-color-overlay);
      border: 1px solid var(--el-border-color-light);
      border-radius: 4px;
      box-shadow: var(--el-box-shadow-light);
      z-index: 1000;
      max-height: 300px;
      overflow-y: auto;
      
      .suggestion-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        cursor: pointer;
        transition: background-color 0.3s;
        
        &:hover {
          background: var(--el-fill-color-light);
        }
        
        .suggestion-icon {
          color: var(--el-color-primary);
        }
        
        .suggestion-content {
          flex: 1;
          
          .suggestion-title {
            font-weight: 500;
            color: var(--el-text-color-primary);
            margin-bottom: 2px;
          }
          
          .suggestion-type {
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }
      }
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quick-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 16px;
}

.action-btn {
  width: 36px;
  height: 36px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-light);
  
  &:hover {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary);
    color: var(--el-color-primary);
  }
}

.lang-item {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .lang-flag {
    font-size: 16px;
  }
}

.notification-dropdown {
  margin-right: 16px;
  
  :deep(.el-dropdown-menu) {
    padding: 0;
    min-width: 320px;
  }
}

.notification-menu {
  .notification-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    font-weight: 500;
  }
  
  .notification-list {
    .notification-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px 16px;
      cursor: pointer;
      transition: background-color 0.3s;
      border-bottom: 1px solid var(--el-border-color-lighter);
      
      &:hover {
        background: var(--el-fill-color-light);
      }
      
      &.unread {
        background: var(--el-color-primary-light-9);
        
        .notification-title {
          font-weight: 600;
        }
      }
      
      &:last-child {
        border-bottom: none;
      }
      
      .notification-icon {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
        margin-top: 2px;
        
        &.info {
          background: var(--el-color-info);
        }
        
        &.success {
          background: var(--el-color-success);
        }
        
        &.warning {
          background: var(--el-color-warning);
        }
        
        &.error {
          background: var(--el-color-error);
        }
      }
      
      .notification-content {
        flex: 1;
        
        .notification-title {
          color: var(--el-text-color-primary);
          margin-bottom: 4px;
          line-height: 1.4;
        }
        
        .notification-message {
          font-size: 13px;
          color: var(--el-text-color-regular);
          line-height: 1.4;
          margin-bottom: 4px;
        }
        
        .notification-time {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }
    }
  }
  
  .notification-footer {
    padding: 12px 16px;
    text-align: center;
    border-top: 1px solid var(--el-border-color-lighter);
  }
}

.user-dropdown {
  .user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.3s;
    
    &:hover {
      background: var(--el-fill-color-light);
    }
    
    .username {
      font-weight: 500;
      color: var(--el-text-color-primary);
    }
    
    .dropdown-icon {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .header-left {
    .search-container {
      max-width: 200px;
    }
  }
  
  .quick-actions {
    gap: 4px;
    margin-right: 8px;
  }
  
  .user-info {
    .username {
      display: none;
    }
  }
}

@media (max-width: 480px) {
  .header-left {
    .search-container {
      display: none;
    }
  }
  
  .quick-actions {
    .action-btn:not(:first-child) {
      display: none;
    }
  }
}
</style>