<template>
  <div id="app" class="app-container">
    <!-- 全局加载遮罩 -->
    <div v-if="appStore.globalLoading" class="global-loading">
      <div class="loading-content">
        <el-icon class="loading-icon" :size="40">
          <Loading />
        </el-icon>
        <p class="loading-text">{{ appStore.loadingText || '加载中...' }}</p>
      </div>
    </div>

    <!-- 主应用内容 -->
    <router-view v-slot="{ Component, route: currentRoute }"> <transition
        :name="transitionName"
        mode="out-in"
        appear
      >
        <keep-alive :include="tabsStore.cachedViews">
          <component :is="Component" :key="currentRoute.fullPath" />
        </keep-alive>
      </transition>
    </router-view>

    <!-- 全局通知容器 -->
    <Teleport to="body">
      <div id="global-notifications"></div>
    </Teleport>

    <!-- 全局模态框容器 -->
    <Teleport to="body">
      <div id="global-modals"></div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { useTabsStore } from '@/stores/tabs'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import NProgress from 'nprogress'

// 状态管理
const appStore = useAppStore()
const userStore = useUserStore()
const tabsStore = useTabsStore()
const router = useRouter()
const route = useRoute() // This is the global route object

// Computed property for transition name to provide stronger type safety
const transitionName = computed(() => {
  // 'route' here refers to the global route object from useRoute()
  if (route.meta && typeof route.meta.transition === 'string' && route.meta.transition) {
    return route.meta.transition;
  }
  return 'fade'; // Default transition name
});

// 监听路由变化
watch(
  () => route.path,
  (newPath, oldPath) => {
    // 更新面包屑
    appStore.updateBreadcrumb(route)
    
    // 添加到标签页
    if (route.meta?.keepAlive !== false) {
      tabsStore.addTab(route)
    }
    
    // 页面切换时的处理
    if (newPath !== oldPath) {
      // 重置页面状态
      appStore.setGlobalLoading(false)
      
      // 滚动到顶部
      nextTick(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      })
    }
  },
  { immediate: true }
)

// 监听网络状态
const handleOnline = () => {
  ElMessage.success('网络连接已恢复')
  appStore.setNetworkStatus(true)
}

const handleOffline = () => {
  ElMessage.warning('网络连接已断开')
  appStore.setNetworkStatus(false)
}

// 监听窗口大小变化
const handleResize = () => {
  appStore.updateWindowSize()
}

// 监听页面可见性变化
const handleVisibilityChange = () => {
  if (document.hidden) {
    appStore.setPageVisible(false)
  } else {
    appStore.setPageVisible(true)
    // 页面重新可见时，刷新用户状态
    if (userStore.isLoggedIn) {
      userStore.refreshUserInfo()
    }
  }
}

// 键盘快捷键处理
const handleKeydown = (event: KeyboardEvent) => {
  // Ctrl/Cmd + K: 打开搜索
  if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
    event.preventDefault()
    appStore.toggleSearch()
  }
  
  // Ctrl/Cmd + /: 打开帮助
  if ((event.ctrlKey || event.metaKey) && event.key === '/') {
    event.preventDefault()
    appStore.toggleHelp()
  }
  
  // Esc: 关闭模态框或搜索
  if (event.key === 'Escape') {
    appStore.closeAllModals()
  }
}

// 组件挂载
onMounted(async () => {
  // 初始化应用
  await appStore.initializeApp()
  
  // 检查用户登录状态
  if (userStore.token) {
    try {
      await userStore.getUserInfo()
    } catch (error) {
      console.error('获取用户信息失败:', error)
      // 如果获取用户信息失败，清除token并跳转到登录页
      userStore.logout()
      router.push('/login')
    }
  }
  
  // 添加事件监听器
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  window.addEventListener('resize', handleResize)
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  
  // 初始化窗口大小
  handleResize()
  
  // 设置初始网络状态
  appStore.setNetworkStatus(navigator.onLine)
  
  // 完成初始化
  NProgress.done()
})

// 组件卸载
onUnmounted(() => {
  // 移除事件监听器
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

// 错误边界处理
const handleError = (error: Error, info: string) => {
  console.error('App Error:', error)
  console.error('Error Info:', info)
  
  // 显示用户友好的错误信息
  ElMessage.error('应用出现错误，请刷新页面重试')
  
  // 可以在这里添加错误上报逻辑
  // errorReporter.report(error, { info, route: route.fullPath })
}

// 暴露错误处理方法
defineExpose({
  handleError
})
</script>

<style lang="scss">
// 全局样式
#app {
  width: 100%;
  min-height: 100vh;
  background-color: var(--el-bg-color-page);
  color: var(--el-text-color-primary);
  transition: all 0.3s ease;
}

.app-container {
  position: relative;
  width: 100%;
  min-height: 100vh;
}

// 全局加载遮罩
.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  
  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    
    .loading-icon {
      animation: spin 1s linear infinite;
      color: var(--el-color-primary);
    }
    
    .loading-text {
      font-size: 14px;
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }
}

// 暗色主题下的加载遮罩
.dark .global-loading {
  background: rgba(0, 0, 0, 0.9);
}

// 页面过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(30px);
  opacity: 0;
}

.slide-left-leave-to {
  transform: translateX(-30px);
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}

.slide-right-enter-from {
  transform: translateX(-30px);
  opacity: 0;
}

.slide-right-leave-to {
  transform: translateX(30px);
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  transform: translateY(30px);
  opacity: 0;
}

.slide-up-leave-to {
  transform: translateY(-30px);
  opacity: 0;
}

// 旋转动画
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .app-container {
    padding: 0;
  }
}

// 滚动条样式
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--el-fill-color-lighter);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: var(--el-border-color-darker);
  border-radius: 3px;
  
  &:hover {
    background: var(--el-border-color-dark);
  }
}

// 选择文本样式
::selection {
  background: var(--el-color-primary-light-7);
  color: var(--el-color-primary);
}

// 焦点样式
:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
  border-radius: 4px;
}

// 禁用状态样式
.disabled {
  opacity: 0.6;
  pointer-events: none;
  user-select: none;
}

// 加载状态样式
.loading {
  position: relative;
  pointer-events: none;
  
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1;
  }
}

// 错误状态样式
.error {
  border-color: var(--el-color-danger) !important;
  
  .el-input__inner,
  .el-textarea__inner {
    border-color: var(--el-color-danger) !important;
  }
}

// 成功状态样式
.success {
  border-color: var(--el-color-success) !important;
  
  .el-input__inner,
  .el-textarea__inner {
    border-color: var(--el-color-success) !important;
  }
}
</style>