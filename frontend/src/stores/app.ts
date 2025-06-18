import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RouteLocationNormalized } from 'vue-router'
import { ElMessage } from 'element-plus'

// 应用设置接口
interface AppSettings {
  theme: 'light' | 'dark' | 'auto'
  language: 'zh-CN' | 'en-US'
  sidebarCollapsed: boolean
  showBreadcrumb: boolean
  showTags: boolean
  showFooter: boolean
  fixedHeader: boolean
  enableTransition: boolean
  transitionName: string
  enableProgress: boolean
  enableKeepAlive: boolean
}

// 窗口尺寸接口
interface WindowSize {
  width: number
  height: number
  isMobile: boolean
  isTablet: boolean
  isDesktop: boolean
}

// 面包屑项接口
interface BreadcrumbItem {
  title: string
  path?: string
  icon?: string
}

export const useAppStore = defineStore('app', () => {
  // 状态
  const globalLoading = ref(false)
  const loadingText = ref('')
  const networkStatus = ref(true)
  const pageVisible = ref(true)
  const routesAdded = ref(false)
  const accessibleRoutes = ref<any[]>([])
  const currentRoute = ref<RouteLocationNormalized | null>(null)
  const breadcrumbs = ref<BreadcrumbItem[]>([])
  
  // 应用配置
  const appConfig = ref({
    title: '企业知识库系统',
    version: '1.0.0',
    description: '基于AI的企业知识管理平台'
  })
  
  // 应用设置
  const settings = ref<AppSettings>({
    theme: 'light',
    language: 'zh-CN',
    sidebarCollapsed: false,
    showBreadcrumb: true,
    showTags: true,
    showFooter: true,
    fixedHeader: true,
    enableTransition: true,
    transitionName: 'fade',
    enableProgress: true,
    enableKeepAlive: true
  })
  
  // 窗口尺寸
  const windowSize = ref<WindowSize>({
    width: window.innerWidth,
    height: window.innerHeight,
    isMobile: window.innerWidth < 768,
    isTablet: window.innerWidth >= 768 && window.innerWidth < 1024,
    isDesktop: window.innerWidth >= 1024
  })
  
  // 模态框状态
  const searchVisible = ref(false)
  const helpVisible = ref(false)
  const settingsVisible = ref(false)
  
  // 计算属性
  const isDark = computed(() => {
    if (settings.value.theme === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return settings.value.theme === 'dark'
  })
  
  const isMobile = computed(() => windowSize.value.isMobile)
  const isTablet = computed(() => windowSize.value.isTablet)
  const isDesktop = computed(() => windowSize.value.isDesktop)
  const language = computed(() => settings.value.language)
  const sidebarCollapsed = computed(() => settings.value.sidebarCollapsed)
  
  // 动作
  const setGlobalLoading = (loading: boolean, text = '') => {
    globalLoading.value = loading
    loadingText.value = text
  }
  
  const setNetworkStatus = (status: boolean) => {
    networkStatus.value = status
  }
  
  const setPageVisible = (visible: boolean) => {
    pageVisible.value = visible
  }
  
  const setRoutesAdded = (added: boolean) => {
    routesAdded.value = added
  }
  
  const setAccessibleRoutes = (routes: any[]) => {
    accessibleRoutes.value = routes
  }
  
  const setCurrentRoute = (route: RouteLocationNormalized) => {
    currentRoute.value = route
  }
  
  const updateBreadcrumb = (route: RouteLocationNormalized) => {
    const breadcrumbList: BreadcrumbItem[] = []
    
    // 添加首页
    breadcrumbList.push({
      title: '首页',
      path: '/dashboard',
      icon: 'House'
    })
    
    // 解析路由路径
    const pathArray = route.path.split('/').filter(path => path)
    let currentPath = ''
    
    pathArray.forEach((path, index) => {
      currentPath += `/${path}`
      
      // 查找匹配的路由
      const matchedRoute = findRouteByPath(currentPath, accessibleRoutes.value)
      
      if (matchedRoute && matchedRoute.meta?.title) {
        breadcrumbList.push({
          title: matchedRoute.meta.title as string,
          path: index === pathArray.length - 1 ? undefined : currentPath,
          icon: matchedRoute.meta.icon as string
        })
      }
    })
    
    breadcrumbs.value = breadcrumbList
  }
  
  const updateWindowSize = () => {
    windowSize.value = {
      width: window.innerWidth,
      height: window.innerHeight,
      isMobile: window.innerWidth < 768,
      isTablet: window.innerWidth >= 768 && window.innerWidth < 1024,
      isDesktop: window.innerWidth >= 1024
    }
    
    // 移动端自动收起侧边栏
    if (windowSize.value.isMobile && !settings.value.sidebarCollapsed) {
      settings.value.sidebarCollapsed = true
    }
  }
  
  const toggleSidebar = () => {
    settings.value.sidebarCollapsed = !settings.value.sidebarCollapsed
    saveSettings()
  }
  
  const toggleTheme = () => {
    settings.value.theme = settings.value.theme === 'light' ? 'dark' : 'light'
    applyTheme()
    saveSettings()
  }
  
  const setTheme = (theme: 'light' | 'dark' | 'auto') => {
    settings.value.theme = theme
    applyTheme()
    saveSettings()
  }
  
  const setLanguage = (language: 'zh-CN' | 'en-US') => {
    settings.value.language = language
    saveSettings()
    
    // 重新加载页面以应用语言变化
    window.location.reload()
  }
  
  const updateSettings = (newSettings: Partial<AppSettings>) => {
    Object.assign(settings.value, newSettings)
    applyTheme()
    saveSettings()
  }
  
  const toggleSearch = () => {
    searchVisible.value = !searchVisible.value
  }
  
  const toggleHelp = () => {
    helpVisible.value = !helpVisible.value
  }
  
  const toggleSettings = () => {
    settingsVisible.value = !settingsVisible.value
  }
  
  const closeAllModals = () => {
    searchVisible.value = false
    helpVisible.value = false
    settingsVisible.value = false
  }
  
  const addVisitedView = (view: any) => {
    // 这里可以添加访问历史的逻辑
    // 暂时只是一个占位方法
    console.log('添加访问视图:', view)
  }
  
  const applyTheme = () => {
    const html = document.documentElement
    
    if (isDark.value) {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }
  
  const saveSettings = () => {
    try {
      localStorage.setItem('app-settings', JSON.stringify(settings.value))
    } catch (error) {
      console.error('保存设置失败:', error)
      ElMessage.warning('设置保存失败')
    }
  }
  
  const loadSettings = () => {
    try {
      const savedSettings = localStorage.getItem('app-settings')
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings)
        Object.assign(settings.value, parsed)
      }
    } catch (error) {
      console.error('加载设置失败:', error)
    }
  }
  
  const initializeApp = async () => {
    try {
      setGlobalLoading(true, '正在初始化应用...')
      
      // 加载设置
      loadSettings()
      
      // 应用主题
      applyTheme()
      
      // 监听系统主题变化
      if (settings.value.theme === 'auto') {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
        mediaQuery.addEventListener('change', applyTheme)
      }
      
      // 更新窗口尺寸
      updateWindowSize()
      
      // 模拟初始化延迟
      await new Promise(resolve => setTimeout(resolve, 500))
      
    } catch (error) {
      console.error('应用初始化失败:', error)
      ElMessage.error('应用初始化失败')
    } finally {
      setGlobalLoading(false)
    }
  }
  
  const resetApp = () => {
    // 重置状态
    globalLoading.value = false
    loadingText.value = ''
    routesAdded.value = false
    accessibleRoutes.value = []
    currentRoute.value = null
    breadcrumbs.value = []
    
    // 重置模态框状态
    closeAllModals()
    
    // 重置设置为默认值
    settings.value = {
      theme: 'light',
      language: 'zh-CN',
      sidebarCollapsed: false,
      showBreadcrumb: true,
      showTags: true,
      showFooter: true,
      fixedHeader: true,
      enableTransition: true,
      transitionName: 'fade',
      enableProgress: true,
      enableKeepAlive: true
    }
    
    // 清除本地存储
    localStorage.removeItem('app-settings')
    
    // 应用默认主题
    applyTheme()
  }
  
  // 辅助函数：根据路径查找路由
  const findRouteByPath = (path: string, routes: any[]): any => {
    for (const route of routes) {
      if (route.path === path) {
        return route
      }
      
      if (route.children) {
        const found = findRouteByPath(path, route.children)
        if (found) {
          return found
        }
      }
    }
    return null
  }
  
  // 添加setLoading别名方法
  const setLoading = (loading: boolean, text?: string) => {
    setGlobalLoading(loading, text)
  }
  

  
  return {
    // 状态
    globalLoading,
    loadingText,
    networkStatus,
    pageVisible,
    routesAdded,
    accessibleRoutes,
    currentRoute,
    breadcrumbs,
    appConfig,
    settings,
    windowSize,
    searchVisible,
    helpVisible,
    settingsVisible,
    
    // 计算属性
    isDark,
    isMobile,
    isTablet,
    isDesktop,
    language,
    sidebarCollapsed,
    
    // 动作
    setGlobalLoading,
    setLoading,
    setNetworkStatus,
    setPageVisible,
    setRoutesAdded,
    setAccessibleRoutes,
    setCurrentRoute,
    updateBreadcrumb,
    updateWindowSize,
    toggleSidebar,
    toggleTheme,
    setTheme,
    setLanguage,
    updateSettings,
    toggleSearch,
    toggleHelp,
    toggleSettings,
    closeAllModals,
    addVisitedView,
    applyTheme,
    saveSettings,
    loadSettings,
    initializeApp,
    resetApp
  }
})