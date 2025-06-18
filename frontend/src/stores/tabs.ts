import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RouteLocationNormalized } from 'vue-router'
import { ElMessage } from 'element-plus'

// 标签页接口
interface TabItem {
  name: string
  path: string
  title: string
  icon?: string
  closable: boolean
  cached: boolean
  params?: Record<string, any>
  query?: Record<string, any>
  meta?: Record<string, any>
}

// 标签页上下文菜单项
interface ContextMenuItem {
  label: string
  icon: string
  action: string
  disabled?: boolean
  divided?: boolean
}

export const useTabsStore = defineStore('tabs', () => {
  // 状态
  const tabs = ref<TabItem[]>([])
  const activeTab = ref<string>('')
  const cachedTabs = ref<Set<string>>(new Set())
  const contextMenuVisible = ref(false)
  const contextMenuPosition = ref({ x: 0, y: 0 })
  const contextMenuTarget = ref<string>('')
  const maxTabs = ref(20) // 最大标签页数量
  
  // 计算属性
  const currentTab = computed(() => {
    return tabs.value.find(tab => tab.name === activeTab.value)
  })
  
  const closableTabs = computed(() => {
    return tabs.value.filter(tab => tab.closable)
  })
  
  const pinnedTabs = computed(() => {
    return tabs.value.filter(tab => !tab.closable)
  })
  
  const canCloseOthers = computed(() => {
    return closableTabs.value.length > 1
  })
  
  const canCloseAll = computed(() => {
    return closableTabs.value.length > 0
  })
  
  const canCloseLeft = computed(() => {
    const targetIndex = tabs.value.findIndex(tab => tab.name === contextMenuTarget.value)
    return targetIndex > 0 && tabs.value.slice(0, targetIndex).some(tab => tab.closable)
  })
  
  const canCloseRight = computed(() => {
    const targetIndex = tabs.value.findIndex(tab => tab.name === contextMenuTarget.value)
    return targetIndex < tabs.value.length - 1 && 
           tabs.value.slice(targetIndex + 1).some(tab => tab.closable)
  })
  
  // 缓存的视图名称列表
  const cachedViews = computed(() => {
    return Array.from(cachedTabs.value)
  })
  
  // 上下文菜单项
  const contextMenuItems = computed((): ContextMenuItem[] => {
    const targetTab = tabs.value.find(tab => tab.name === contextMenuTarget.value)
    
    return [
      {
        label: '刷新',
        icon: 'Refresh',
        action: 'refresh'
      },
      {
        label: '关闭',
        icon: 'Close',
        action: 'close',
        disabled: !targetTab?.closable
      },
      {
        label: '关闭其他',
        icon: 'CircleClose',
        action: 'closeOthers',
        disabled: !canCloseOthers.value,
        divided: true
      },
      {
        label: '关闭左侧',
        icon: 'Back',
        action: 'closeLeft',
        disabled: !canCloseLeft.value
      },
      {
        label: '关闭右侧',
        icon: 'Right',
        action: 'closeRight',
        disabled: !canCloseRight.value
      },
      {
        label: '关闭全部',
        icon: 'CircleCloseFilled',
        action: 'closeAll',
        disabled: !canCloseAll.value,
        divided: true
      },
      {
        label: targetTab?.cached ? '取消缓存' : '缓存页面',
        icon: targetTab?.cached ? 'RemoveFilled' : 'DocumentAdd',
        action: 'toggleCache'
      }
    ]
  })
  
  // 动作
  const addTab = (route: RouteLocationNormalized) => {
    const { name, path, meta, params, query } = route
    
    if (!name || typeof name !== 'string') {
      return
    }
    
    // 检查标签页是否已存在
    const existingTab = tabs.value.find(tab => tab.name === name)
    
    if (existingTab) {
      // 更新现有标签页信息
      existingTab.path = path
      existingTab.params = params
      existingTab.query = query
      existingTab.meta = meta
      
      // 激活标签页
      activeTab.value = name
      return
    }
    
    // 检查标签页数量限制
    if (tabs.value.length >= maxTabs.value) {
      // 移除最旧的可关闭标签页
      const oldestClosableIndex = tabs.value.findIndex(tab => tab.closable)
      if (oldestClosableIndex !== -1) {
        const removedTab = tabs.value.splice(oldestClosableIndex, 1)[0]
        removeCachedTab(removedTab.name)
        ElMessage.warning(`已自动关闭标签页: ${removedTab.title}`)
      } else {
        ElMessage.warning('标签页数量已达上限')
        return
      }
    }
    
    // 创建新标签页
    const newTab: TabItem = {
      name,
      path,
      title: typeof meta?.title === 'string' ? meta.title : name,
      icon: typeof meta?.icon === 'string' ? meta.icon : undefined,
      closable: typeof meta?.closable === 'boolean' ? meta.closable : true, // 默认可关闭
      cached: typeof meta?.keepAlive === 'boolean' ? meta.keepAlive : false, // 默认不缓存
      params,
      query,
      meta
    }
    
    tabs.value.push(newTab)
    activeTab.value = name
    
    // 如果需要缓存，添加到缓存集合
    if (newTab.cached) {
      cachedTabs.value.add(name)
    }
    
    // 保存到本地存储
    saveTabs()
  }
  
  const removeTab = (tabName: string) => {
    const tabIndex = tabs.value.findIndex(tab => tab.name === tabName)
    
    if (tabIndex === -1) {
      return
    }
    
    const tab = tabs.value[tabIndex]
    
    // 检查是否可关闭
    if (!tab.closable) {
      ElMessage.warning('该标签页不能关闭')
      return
    }
    
    // 移除标签页
    tabs.value.splice(tabIndex, 1)
    
    // 移除缓存
    removeCachedTab(tabName)
    
    // 如果关闭的是当前激活标签页，需要激活其他标签页
    if (activeTab.value === tabName) {
      if (tabs.value.length > 0) {
        // 激活相邻的标签页
        const newActiveIndex = Math.min(tabIndex, tabs.value.length - 1)
        activeTab.value = tabs.value[newActiveIndex].name
      } else {
        activeTab.value = ''
      }
    }
    
    // 保存到本地存储
    saveTabs()
  }
  
  const closeOtherTabs = (keepTabName?: string) => {
    const targetTab = keepTabName || activeTab.value
    
    // 保留不可关闭的标签页和指定的标签页
    const newTabs = tabs.value.filter(tab => 
      !tab.closable || tab.name === targetTab
    )
    
    // 清除被移除标签页的缓存
    tabs.value.forEach(tab => {
      if (tab.closable && tab.name !== targetTab) {
        removeCachedTab(tab.name)
      }
    })
    
    tabs.value = newTabs
    
    // 确保激活正确的标签页
    if (targetTab && tabs.value.some(tab => tab.name === targetTab)) {
      activeTab.value = targetTab
    } else if (tabs.value.length > 0) {
      activeTab.value = tabs.value[0].name
    } else {
      activeTab.value = ''
    }
    
    saveTabs()
  }
  
  const closeLeftTabs = (tabName: string) => {
    const tabIndex = tabs.value.findIndex(tab => tab.name === tabName)
    
    if (tabIndex <= 0) {
      return
    }
    
    // 移除左侧可关闭的标签页
    const leftTabs = tabs.value.slice(0, tabIndex)
    const removedTabs = leftTabs.filter(tab => tab.closable)
    
    removedTabs.forEach(tab => {
      removeCachedTab(tab.name)
    })
    
    tabs.value = [
      ...leftTabs.filter(tab => !tab.closable),
      ...tabs.value.slice(tabIndex)
    ]
    
    saveTabs()
  }
  
  const closeRightTabs = (tabName: string) => {
    const tabIndex = tabs.value.findIndex(tab => tab.name === tabName)
    
    if (tabIndex === -1 || tabIndex >= tabs.value.length - 1) {
      return
    }
    
    // 移除右侧可关闭的标签页
    const rightTabs = tabs.value.slice(tabIndex + 1)
    const removedTabs = rightTabs.filter(tab => tab.closable)
    
    removedTabs.forEach(tab => {
      removeCachedTab(tab.name)
    })
    
    tabs.value = [
      ...tabs.value.slice(0, tabIndex + 1),
      ...rightTabs.filter(tab => !tab.closable)
    ]
    
    saveTabs()
  }
  
  const closeAllTabs = () => {
    // 保留不可关闭的标签页
    const pinnedTabs = tabs.value.filter(tab => !tab.closable)
    
    // 清除所有可关闭标签页的缓存
    tabs.value.forEach(tab => {
      if (tab.closable) {
        removeCachedTab(tab.name)
      }
    })
    
    tabs.value = pinnedTabs
    
    // 激活第一个固定标签页或清空
    if (pinnedTabs.length > 0) {
      activeTab.value = pinnedTabs[0].name
    } else {
      activeTab.value = ''
    }
    
    saveTabs()
  }
  
  const setActiveTab = (tabName: string) => {
    const tab = tabs.value.find(tab => tab.name === tabName)
    
    if (tab) {
      activeTab.value = tabName
      saveTabs()
    }
  }
  
  const toggleTabCache = (tabName: string) => {
    const tab = tabs.value.find(tab => tab.name === tabName)
    
    if (tab) {
      tab.cached = !tab.cached
      
      if (tab.cached) {
        cachedTabs.value.add(tabName)
      } else {
        cachedTabs.value.delete(tabName)
      }
      
      saveTabs()
    }
  }
  
  const refreshTab = (tabName?: string) => {
    const targetTab = tabName || activeTab.value
    
    if (targetTab) {
      // 移除缓存以强制刷新
      removeCachedTab(targetTab)
      
      // 重新添加到缓存（如果标签页设置为缓存）
      const tab = tabs.value.find(tab => tab.name === targetTab)
      if (tab?.cached) {
        cachedTabs.value.add(targetTab)
      }
    }
  }
  
  const showContextMenu = (event: MouseEvent, tabName: string) => {
    event.preventDefault()
    
    contextMenuTarget.value = tabName
    contextMenuPosition.value = {
      x: event.clientX,
      y: event.clientY
    }
    contextMenuVisible.value = true
    
    // 点击其他地方关闭菜单
    const closeMenu = () => {
      contextMenuVisible.value = false
      document.removeEventListener('click', closeMenu)
    }
    
    setTimeout(() => {
      document.addEventListener('click', closeMenu)
    }, 0)
  }
  
  const handleContextMenuAction = (action: string) => {
    const targetTab = contextMenuTarget.value
    
    switch (action) {
      case 'refresh':
        refreshTab(targetTab)
        break
      case 'close':
        removeTab(targetTab)
        break
      case 'closeOthers':
        closeOtherTabs(targetTab)
        break
      case 'closeLeft':
        closeLeftTabs(targetTab)
        break
      case 'closeRight':
        closeRightTabs(targetTab)
        break
      case 'closeAll':
        closeAllTabs()
        break
      case 'toggleCache':
        toggleTabCache(targetTab)
        break
    }
    
    contextMenuVisible.value = false
  }
  
  const removeCachedTab = (tabName: string) => {
    cachedTabs.value.delete(tabName)
  }
  
  const saveTabs = () => {
    try {
      const tabsData = {
        tabs: tabs.value,
        activeTab: activeTab.value,
        cachedTabs: Array.from(cachedTabs.value)
      }
      
      localStorage.setItem('tabs-data', JSON.stringify(tabsData))
    } catch (error) {
      console.error('保存标签页数据失败:', error)
    }
  }
  
  const loadTabs = () => {
    try {
      const tabsData = localStorage.getItem('tabs-data')
      
      if (tabsData) {
        const parsed = JSON.parse(tabsData)
        
        tabs.value = parsed.tabs || []
        activeTab.value = parsed.activeTab || ''
        cachedTabs.value = new Set(parsed.cachedTabs || [])
      }
    } catch (error) {
      console.error('加载标签页数据失败:', error)
      clearTabs()
    }
  }
  
  const clearTabs = () => {
    tabs.value = []
    activeTab.value = ''
    cachedTabs.value.clear()
    
    try {
      localStorage.removeItem('tabs-data')
    } catch (error) {
      console.error('清除标签页数据失败:', error)
    }
  }
  
  const resetTabs = () => {
    clearTabs()
    
    // 添加默认首页标签
    const homeTab: TabItem = {
      name: 'Dashboard',
      path: '/dashboard',
      title: '首页',
      icon: 'House',
      closable: false,
      cached: true
    }
    
    tabs.value = [homeTab]
    activeTab.value = 'Dashboard'
    cachedTabs.value.add('Dashboard')
    
    saveTabs()
  }
  
  // 初始化时加载标签页数据
  loadTabs()
  
  return {
    // 状态
    tabs,
    activeTab,
    cachedTabs,
    contextMenuVisible,
    contextMenuPosition,
    contextMenuTarget,
    maxTabs,
    
    // 计算属性
    currentTab,
    closableTabs,
    pinnedTabs,
    canCloseOthers,
    canCloseAll,
    canCloseLeft,
    canCloseRight,
    cachedViews,
    contextMenuItems,
    
    // 动作
    addTab,
    removeTab,
    closeOtherTabs,
    closeLeftTabs,
    closeRightTabs,
    closeAllTabs,
    setActiveTab,
    toggleTabCache,
    refreshTab,
    showContextMenu,
    handleContextMenuAction,
    removeCachedTab,
    saveTabs,
    loadTabs,
    clearTabs,
    resetTabs
  }
})