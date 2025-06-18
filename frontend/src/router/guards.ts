import type { Router, RouteLocationNormalized, NavigationGuardNext } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { useTabsStore } from '@/stores/tabs'
import { getToken, isTokenExpired } from '@/utils/auth'
import { ElMessage } from 'element-plus'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 配置 NProgress
NProgress.configure({
  showSpinner: false,
  speed: 500,
  minimum: 0.1
})

/**
 * 白名单路由（不需要认证）
 */
const whiteList = [
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
  '/404',
  '/403',
  '/500'
]

/**
 * 检查路由是否在白名单中
 * @param path 路由路径
 * @returns 是否在白名单中
 */
const isWhiteList = (path: string): boolean => {
  return whiteList.some(whitePath => {
    if (whitePath.includes('*')) {
      // 支持通配符匹配
      const regex = new RegExp(whitePath.replace(/\*/g, '.*'))
      return regex.test(path)
    }
    return path === whitePath || path.startsWith(whitePath + '/')
  })
}

/**
 * 检查用户是否有访问权限
 * @param permissions 用户权限
 * @param roles 用户角色
 * @param route 目标路由
 * @returns 是否有权限
 */
const hasPermission = (
  permissions: string[],
  roles: string[],
  route: RouteLocationNormalized
): boolean => {
  const meta = route.meta || {}
  
  // 检查权限
  if (meta.permissions && (meta.permissions as string[]).length > 0) {
    const hasRequiredPermission = (meta.permissions as string[]).some((permission: string) =>
      permissions.includes(permission)
    )
    if (!hasRequiredPermission) return false
  }
  
  // 检查角色
  if (meta.roles && (meta.roles as string[]).length > 0) {
    const hasRequiredRole = (meta.roles as string[]).some((role: string) => roles.includes(role))
    if (!hasRequiredRole) return false
  }
  
  return true
}

/**
 * 前置守卫
 * @param to 目标路由
 * @param from 来源路由
 * @param next 导航函数
 */
const beforeEachGuard = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  // 开始进度条
  NProgress.start()
  
  const userStore = useUserStore()
  const appStore = useAppStore()
  const token = getToken()
  
  try {
    // 设置页面标题
    if (to.meta?.title) {
      document.title = `${to.meta.title} - ${appStore.appConfig.title}`
    } else {
      document.title = appStore.appConfig.title
    }
    
    // 如果有 token
    if (token) {
      // 检查 token 是否过期
      if (isTokenExpired(token)) {
        ElMessage.warning('登录已过期，请重新登录')
        await userStore.logout()
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
      
      // 如果访问登录页，重定向到首页
      if (to.path === '/login') {
        next({ path: '/' })
        return
      }
      
      // 如果用户信息不存在，获取用户信息
      if (!userStore.userInfo) {
        try {
          await userStore.getUserProfile()
        } catch (error) {
          console.error('获取用户信息失败:', error)
          ElMessage.error('获取用户信息失败，请重新登录')
          await userStore.logout()
          next({ path: '/login', query: { redirect: to.fullPath } })
          return
        }
      }
      
      // 检查路由权限
      if (to.meta?.requiresAuth !== false) {
        const permissions = userStore.permissions || []
        const roles = userStore.roles || []
        
        if (!hasPermission(permissions, roles, to)) {
          ElMessage.error('权限不足，无法访问该页面')
          next({ path: '/403' })
          return
        }
      }
      
      // 检查开发环境专用路由
      if (to.meta?.devOnly && !import.meta.env.DEV) {
        next({ path: '/404' })
        return
      }
      
      next()
    } else {
      // 没有 token
      if (isWhiteList(to.path)) {
        // 在白名单中，直接访问
        next()
      } else {
        // 不在白名单中，重定向到登录页
        next({ path: '/login', query: { redirect: to.fullPath } })
      }
    }
  } catch (error) {
    console.error('路由守卫错误:', error)
    ElMessage.error('页面加载失败')
    next({ path: '/500' })
  }
}

/**
 * 后置守卫
 * @param to 目标路由
 * @param from 来源路由
 */
const afterEachGuard = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized
) => {
  // 结束进度条
  NProgress.done()
  
  const appStore = useAppStore()
  
  // 添加到访问历史
  if (to.meta?.title && to.path !== from.path) {
    appStore.addVisitedView({
      name: to.name as string,
      path: to.path,
      title: to.meta.title,
      meta: to.meta
    })
  }
  
  // 更新面包屑
  if (to.meta?.breadcrumb !== false) {
    // 这里可以更新面包屑导航
    // appStore.updateBreadcrumbs(getBreadcrumbs(to, routes))
  }
  
  // 页面埋点统计
  if (import.meta.env.PROD) {
    // 这里可以添加页面访问统计
    console.log('页面访问:', {
      path: to.path,
      title: to.meta?.title,
      timestamp: new Date().toISOString()
    })
  }
}

/**
 * 路由错误处理
 * @param error 错误对象
 * @param to 目标路由
 * @param from 来源路由
 */
const onError = (
  error: Error,
  to: RouteLocationNormalized,
  from: RouteLocationNormalized
) => {
  console.error('路由错误:', error)
  
  // 结束进度条
  NProgress.done()
  
  // 显示错误消息
  ElMessage.error('页面加载失败，请稍后重试')
  
  // 可以根据错误类型进行不同处理
  if (error.message.includes('Loading chunk')) {
    // 代码分割加载失败，可能是网络问题或版本更新
    ElMessage.warning('检测到新版本，正在刷新页面...')
    setTimeout(() => {
      window.location.reload()
    }, 1000)
  }
}

/**
 * 动态路由加载守卫
 * @param to 目标路由
 * @param from 来源路由
 * @param next 导航函数
 */
const dynamicRouteGuard = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  const userStore = useUserStore()
  
  // 如果用户已登录且路由未初始化
  if (userStore.userInfo && !userStore.routesInitialized) {
    try {
      // 根据用户权限动态添加路由
      await userStore.initializeRoutes()
      
      // 重新导航到目标路由
      next({ ...to, replace: true })
    } catch (error) {
      console.error('动态路由初始化失败:', error)
      next()
    }
  } else {
    next()
  }
}

/**
 * 页面缓存守卫
 * @param to 目标路由
 * @param from 来源路由
 * @param next 导航函数
 */
const keepAliveGuard = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  const tabsStore = useTabsStore()
  
  // 处理页面缓存
  if (to.meta?.keepAlive && to.name && typeof to.name === 'string') {
    tabsStore.toggleTabCache(to.name)
  }
  
  if (from.meta?.keepAlive === false && from.name && typeof from.name === 'string') {
    // Assuming toggleTabCache with one argument means to remove it or set to false
    // If it needs a boolean, this logic might need adjustment based on toggleTabCache's actual behavior
    tabsStore.toggleTabCache(from.name)
  }
  
  next()
}

/**
 * 外部链接守卫
 * @param to 目标路由
 * @param from 来源路由
 * @param next 导航函数
 */
const externalLinkGuard = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  // 处理外部链接
  if (to.meta?.externalLink) {
    const target = (to.meta.target as string) || '_blank'
    window.open(to.meta.externalLink as string, target)
    next(false) // 阻止路由跳转
    return
  }
  
  next()
}

/**
 * 安装路由守卫
 * @param router 路由实例
 */
export const setupRouterGuards = (router: Router) => {
  // 前置守卫（按顺序执行）
  router.beforeEach(externalLinkGuard)
  router.beforeEach(dynamicRouteGuard)
  router.beforeEach(keepAliveGuard)
  router.beforeEach(beforeEachGuard)
  
  // 后置守卫
  router.afterEach(afterEachGuard)
  
  // 错误处理
  router.onError(onError)
}

/**
 * 路由守卫工具函数
 */
export const routeGuardUtils = {
  /**
   * 检查是否为白名单路由
   */
  isWhiteList,
  
  /**
   * 检查用户权限
   */
  hasPermission,
  
  /**
   * 添加白名单路由
   * @param paths 路由路径数组
   */
  addWhiteList(paths: string[]) {
    whiteList.push(...paths)
  },
  
  /**
   * 移除白名单路由
   * @param path 路由路径
   */
  removeWhiteList(path: string) {
    const index = whiteList.indexOf(path)
    if (index > -1) {
      whiteList.splice(index, 1)
    }
  },
  
  /**
   * 获取白名单
   */
  getWhiteList() {
    return [...whiteList]
  }
}

export default setupRouterGuards