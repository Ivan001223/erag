<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <AppSidebar 
      v-model:collapsed="sidebarCollapsed"
      :class="{ 'sidebar-collapsed': sidebarCollapsed }"
    />
    
    <!-- 主内容区域 -->
    <div class="app-main" :class="{ 'main-expanded': sidebarCollapsed }">
      <!-- 顶部导航 -->
      <AppHeader 
        v-model:sidebar-collapsed="sidebarCollapsed"
        class="app-header"
      />
      
      <!-- 面包屑导航 -->
      <AppBreadcrumb class="app-breadcrumb" />
      
      <!-- 标签页 -->
      <AppTabs class="app-tabs" />
      
      <!-- 页面内容 -->
      <div class="app-content">
        <router-view v-slot="{ Component, route }">
          <transition name="fade-transform" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" :key="route.path" />
            </keep-alive>
          </transition>
        </router-view>
      </div>
      
      <!-- 底部 -->
      <AppFooter class="app-footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { useTabsStore } from '../../stores/tabs'

const appStore = useAppStore()
const tabsStore = useTabsStore()

// 侧边栏折叠状态
const sidebarCollapsed = computed({
  get: () => appStore.sidebarCollapsed,
  set: (value: boolean) => {
    appStore.updateSettings({ sidebarCollapsed: value })
  }
})

// 缓存的视图
const cachedViews = computed(() => tabsStore.cachedViews)
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 240px;
  transition: margin-left 0.3s ease;
  
  &.main-expanded {
    margin-left: 64px;
  }
}

.app-header {
  height: 60px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
  z-index: 100;
}

.app-breadcrumb {
  height: 40px;
  padding: 0 16px;
  background: var(--el-bg-color-page);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.app-tabs {
  height: 40px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.app-content {
  flex: 1;
  padding: 16px;
  background: var(--el-bg-color-page);
  overflow: auto;
}

.app-footer {
  height: 40px;
  border-top: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
}

// 页面切换动画
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}
</style>