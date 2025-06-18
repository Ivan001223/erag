<template>
  <div class="app-tabs" v-show="visitedViews.length > 0">
    <div class="tabs-container">
      <!-- 左侧滚动按钮 -->
      <el-button 
        v-show="showScrollButtons"
        class="scroll-btn scroll-left"
        @click="scrollLeft"
        :disabled="scrollLeftDisabled"
        circle
        size="small"
      >
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      
      <!-- 标签页容器 -->
      <div 
        ref="tabsWrapperRef" 
        class="tabs-wrapper"
        @wheel="handleWheel"
      >
        <div 
          ref="tabsContentRef"
          class="tabs-content"
          :style="{ transform: `translateX(${translateX}px)` }"
        >
          <div
            v-for="view in visitedViews"
            :key="view.path"
            class="tab-item"
            :class="{
              'is-active': isActive(view),
              'is-affix': view.meta?.affix
            }"
            @click="handleTabClick(view)"
            @contextmenu.prevent="handleContextMenu($event, view)"
          >
            <!-- 标签图标 -->
            <el-icon v-if="view.meta?.icon" class="tab-icon">
              <component :is="view.meta.icon" />
            </el-icon>
            
            <!-- 标签标题 -->
            <span class="tab-title">{{ getTabTitle(view) }}</span>
            
            <!-- 关闭按钮 -->
            <el-icon 
              v-if="!view.meta?.affix && visitedViews.length > 1"
              class="tab-close"
              @click.stop="closeTab(view)"
            >
              <Close />
            </el-icon>
          </div>
        </div>
      </div>
      
      <!-- 右侧滚动按钮 -->
      <el-button 
        v-show="showScrollButtons"
        class="scroll-btn scroll-right"
        @click="scrollRight"
        :disabled="scrollRightDisabled"
        circle
        size="small"
      >
        <el-icon><ArrowRight /></el-icon>
      </el-button>
      
      <!-- 操作按钮 -->
      <div class="tabs-actions">
        <!-- 刷新当前页 -->
        <el-tooltip content="刷新当前页">
          <el-button 
            class="action-btn"
            @click="refreshCurrentTab"
            circle
            size="small"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-tooltip>
        
        <!-- 更多操作 -->
        <el-dropdown @command="handleCommand" trigger="click">
          <el-button class="action-btn" circle size="small">
            <el-icon><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="refresh">
                <el-icon><Refresh /></el-icon>
                刷新当前页
              </el-dropdown-item>
              <el-dropdown-item command="close-current" :disabled="currentView?.meta?.affix">
                <el-icon><Close /></el-icon>
                关闭当前页
              </el-dropdown-item>
              <el-dropdown-item command="close-others">
                <el-icon><SemiSelect /></el-icon>
                关闭其他页
              </el-dropdown-item>
              <el-dropdown-item command="close-left">
                <el-icon><Back /></el-icon>
                关闭左侧页
              </el-dropdown-item>
              <el-dropdown-item command="close-right">
                <el-icon><Right /></el-icon>
                关闭右侧页
              </el-dropdown-item>
              <el-dropdown-item command="close-all">
                <el-icon><CircleClose /></el-icon>
                关闭所有页
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <!-- 右键菜单 -->
    <div 
      v-show="contextMenuVisible"
      ref="contextMenuRef"
      class="context-menu"
      :style="contextMenuStyle"
    >
      <div class="context-menu-item" @click="refreshTab(selectedView)">
        <el-icon><Refresh /></el-icon>
        <span>刷新</span>
      </div>
      <div 
        class="context-menu-item" 
        :class="{ disabled: selectedView?.meta?.affix }"
        @click="closeTab(selectedView)"
      >
        <el-icon><Close /></el-icon>
        <span>关闭</span>
      </div>
      <div class="context-menu-item" @click="closeOtherTabs(selectedView)">
        <el-icon><SemiSelect /></el-icon>
        <span>关闭其他</span>
      </div>
      <div class="context-menu-item" @click="() => selectedView && closeLeftTabs(selectedView)">
        <el-icon><Back /></el-icon>
        <span>关闭左侧</span>
      </div>
      <div class="context-menu-item" @click="() => selectedView && closeRightTabs(selectedView)">
        <el-icon><Right /></el-icon>
        <span>关闭右侧</span>
      </div>
      <div class="context-menu-item" @click="closeAllTabs">
        <el-icon><CircleClose /></el-icon>
        <span>关闭所有</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter, type RouteLocationNormalized } from 'vue-router'
import { useTabsStore } from '@/stores/tabs'
import {
  ArrowLeft, ArrowRight, Close, Refresh, MoreFilled,
  SemiSelect, Back, Right, CircleClose
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const tabsStore = useTabsStore()

// 模板引用
const tabsWrapperRef = ref<HTMLElement>()
const tabsContentRef = ref<HTMLElement>()
const contextMenuRef = ref<HTMLElement>()

// 滚动相关
const translateX = ref(0)
const showScrollButtons = ref(false)
const scrollLeftDisabled = ref(true)
const scrollRightDisabled = ref(true)

// 右键菜单相关
const contextMenuVisible = ref(false)
const contextMenuStyle = ref({})
const selectedView = ref<any>(null)

// 计算属性
const visitedViews = computed(() => tabsStore.tabs.map(tab => ({
  name: tab.name as string,
  path: tab.path,
  meta: tab.meta || {},
  params: tab.params || {},
  query: tab.query || {},
  matched: [],
  fullPath: tab.path,
  hash: '',
  redirectedFrom: undefined
})))
const currentView = computed(() => {
  return visitedViews.value.find(view => isActive(view))
})

// 判断标签是否激活
const isActive = (view: any) => {
  return view.path === route.path
}

// 获取标签标题
const getTabTitle = (view: RouteLocationNormalized) => {
  return view.meta?.title || view.name || '未命名页面'
}

// 处理标签点击
const handleTabClick = (view: RouteLocationNormalized) => {
  if (view.path !== route.path) {
    router.push(view.path)
  }
}

// 关闭标签
const closeTab = (view: any) => {
  if (!view || view.meta?.affix) return
  
  const index = visitedViews.value.findIndex(v => v.path === view.path)
  tabsStore.removeTab(view.name as string)
  
  // 如果关闭的是当前标签，需要跳转到其他标签
  if (isActive(view)) {
    const nextView = visitedViews.value[index] || visitedViews.value[index - 1]
    if (nextView) {
      router.push(nextView.path)
    } else {
      router.push('/dashboard')
    }
  }
  
  hideContextMenu()
}

// 刷新标签
const refreshTab = (view: any) => {
  if (!view) return
  
  if (isActive(view)) {
    refreshCurrentTab()
  } else {
    // 如果不是当前标签，先跳转再刷新
    router.push(view.path).then(() => {
      refreshCurrentTab()
    })
  }
  
  hideContextMenu()
}

// 刷新当前标签
const refreshCurrentTab = () => {
  // 这里可以触发页面刷新事件
  // 具体实现可能需要配合页面组件的 key 值变化
  tabsStore.refreshTab(route.name as string)
}

// 关闭其他标签
const closeOtherTabs = (view: any) => {
  if (!view) return
  
  tabsStore.closeOtherTabs(view.name as string)
  
  if (!isActive(view)) {
    router.push(view.path)
  }
  
  hideContextMenu()
}

// 关闭左侧标签
const closeLeftTabs = (view: any) => {
  if (!view) return
  
  tabsStore.closeLeftTabs(view.name as string)
  hideContextMenu()
}

// 关闭右侧标签
const closeRightTabs = (view: any) => {
  if (!view) return
  
  tabsStore.closeRightTabs(view.name as string)
  hideContextMenu()
}

// 关闭所有标签
const closeAllTabs = () => {
  tabsStore.closeAllTabs()
  router.push('/dashboard')
  hideContextMenu()
}

// 处理右键菜单
const handleContextMenu = (event: MouseEvent, view: any) => {
  event.preventDefault()
  
  selectedView.value = view
  contextMenuVisible.value = true
  
  nextTick(() => {
    const menu = contextMenuRef.value
    if (!menu) return
    
    const { clientX, clientY } = event
    const { innerWidth, innerHeight } = window
    const menuWidth = menu.offsetWidth
    const menuHeight = menu.offsetHeight
    
    let left = clientX
    let top = clientY
    
    // 防止菜单超出屏幕
    if (clientX + menuWidth > innerWidth) {
      left = clientX - menuWidth
    }
    
    if (clientY + menuHeight > innerHeight) {
      top = clientY - menuHeight
    }
    
    contextMenuStyle.value = {
      left: `${left}px`,
      top: `${top}px`
    }
  })
}

// 隐藏右键菜单
const hideContextMenu = () => {
  contextMenuVisible.value = false
  selectedView.value = null
}

// 处理下拉菜单命令
const handleCommand = (command: string) => {
  switch (command) {
    case 'refresh':
      refreshCurrentTab()
      break
    case 'close-current':
      closeTab(currentView.value)
      break
    case 'close-others':
      closeOtherTabs(currentView.value)
      break
    case 'close-left':
      closeLeftTabs(currentView.value)
      break
    case 'close-right':
      closeRightTabs(currentView.value)
      break
    case 'close-all':
      closeAllTabs()
      break
  }
}

// 滚动相关方法
const updateScrollButtons = () => {
  if (!tabsWrapperRef.value || !tabsContentRef.value) return
  
  const wrapperWidth = tabsWrapperRef.value.offsetWidth
  const contentWidth = tabsContentRef.value.offsetWidth
  
  showScrollButtons.value = contentWidth > wrapperWidth
  scrollLeftDisabled.value = translateX.value >= 0
  scrollRightDisabled.value = translateX.value <= wrapperWidth - contentWidth
}

const scrollLeft = () => {
  const scrollDistance = 200
  translateX.value = Math.min(translateX.value + scrollDistance, 0)
  updateScrollButtons()
}

const scrollRight = () => {
  if (!tabsWrapperRef.value || !tabsContentRef.value) return
  
  const scrollDistance = 200
  const wrapperWidth = tabsWrapperRef.value.offsetWidth
  const contentWidth = tabsContentRef.value.offsetWidth
  const minTranslateX = wrapperWidth - contentWidth
  
  translateX.value = Math.max(translateX.value - scrollDistance, minTranslateX)
  updateScrollButtons()
}

// 鼠标滚轮滚动
const handleWheel = (event: WheelEvent) => {
  event.preventDefault()
  
  if (event.deltaY > 0) {
    scrollRight()
  } else {
    scrollLeft()
  }
}

// 滚动到激活的标签
const scrollToActiveTab = () => {
  if (!tabsWrapperRef.value || !tabsContentRef.value) return
  
  const activeTab = tabsContentRef.value.querySelector('.tab-item.is-active') as HTMLElement
  if (!activeTab) return
  
  const wrapperWidth = tabsWrapperRef.value.offsetWidth
  const tabLeft = activeTab.offsetLeft
  const tabWidth = activeTab.offsetWidth
  
  // 如果标签在可视区域外，滚动到合适位置
  if (tabLeft + translateX.value < 0) {
    translateX.value = -tabLeft + 20
  } else if (tabLeft + tabWidth + translateX.value > wrapperWidth) {
    translateX.value = wrapperWidth - tabLeft - tabWidth - 20
  }
  
  updateScrollButtons()
}

// 监听路由变化，添加标签
watch(
  () => route.path,
  () => {
    tabsStore.addTab(route)
    nextTick(() => {
      updateScrollButtons()
      scrollToActiveTab()
    })
  },
  { immediate: true }
)

// 监听标签变化，更新滚动按钮
watch(
  () => visitedViews.value.length,
  () => {
    nextTick(() => {
      updateScrollButtons()
    })
  }
)

// 点击其他地方隐藏右键菜单
const handleClickOutside = (event: MouseEvent) => {
  if (contextMenuVisible.value && !contextMenuRef.value?.contains(event.target as Node)) {
    hideContextMenu()
  }
}

// 组件挂载时添加事件监听
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('resize', updateScrollButtons)
  
  nextTick(() => {
    updateScrollButtons()
  })
})

// 组件卸载时移除事件监听
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('resize', updateScrollButtons)
})
</script>

<style lang="scss" scoped>
.app-tabs {
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-lighter);
  user-select: none;
}

.tabs-container {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 8px;
  gap: 8px;
}

.scroll-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-light);
  
  &:hover:not(:disabled) {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary);
    color: var(--el-color-primary);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.tabs-wrapper {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.tabs-content {
  display: flex;
  transition: transform 0.3s ease;
  gap: 4px;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 32px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
  flex-shrink: 0;
  
  &:hover {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary-light-5);
    
    .tab-close {
      opacity: 1;
    }
  }
  
  &.is-active {
    background: var(--el-color-primary);
    border-color: var(--el-color-primary);
    color: white;
    
    .tab-icon,
    .tab-title,
    .tab-close {
      color: white;
    }
  }
  
  &.is-affix {
    .tab-close {
      display: none;
    }
  }
}

.tab-icon {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.tab-title {
  font-size: 13px;
  color: var(--el-text-color-primary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-close {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  opacity: 0;
  transition: opacity 0.3s ease;
  
  &:hover {
    color: var(--el-color-error);
  }
}

.tabs-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.action-btn {
  width: 28px;
  height: 28px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-light);
  
  &:hover {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary);
    color: var(--el-color-primary);
  }
}

.context-menu {
  position: fixed;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  box-shadow: var(--el-box-shadow-light);
  z-index: 3000;
  padding: 4px 0;
  min-width: 120px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: var(--el-text-color-primary);
  transition: background-color 0.3s ease;
  
  &:hover:not(.disabled) {
    background: var(--el-fill-color-light);
  }
  
  &.disabled {
    color: var(--el-text-color-disabled);
    cursor: not-allowed;
  }
  
  .el-icon {
    font-size: 14px;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .tabs-container {
    padding: 0 4px;
    gap: 4px;
  }
  
  .tab-item {
    padding: 0 8px;
    gap: 4px;
    
    .tab-title {
      max-width: 80px;
    }
  }
  
  .scroll-btn,
  .action-btn {
    width: 24px;
    height: 24px;
  }
}

@media (max-width: 480px) {
  .tabs-container {
    height: 36px;
  }
  
  .tab-item {
    height: 28px;
    padding: 0 6px;
    
    .tab-title {
      max-width: 60px;
      font-size: 12px;
    }
    
    .tab-icon {
      font-size: 12px;
    }
  }
  
  .tabs-actions {
    .action-btn:not(:first-child) {
      display: none;
    }
  }
}
</style>