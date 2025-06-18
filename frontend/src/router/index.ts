import { createRouter, createWebHistory } from 'vue-router'
import type { RouteLocationNormalized, NavigationGuardNext, RouteLocationNormalizedLoaded, RouteRecordRaw } from 'vue-router'
import { routes } from './routes'
import { setupRouterGuards } from './guards'

// 路由常量
export const ROUTE_NAMES = {
  // 认证相关
  LOGIN: 'Login',
  REGISTER: 'Register',
  FORGOT_PASSWORD: 'ForgotPassword',
  RESET_PASSWORD: 'ResetPassword',
  
  // 主要页面
  DASHBOARD: 'Dashboard',
  PROFILE: 'Profile',
  
  // 知识管理
  DOCUMENT_LIST: 'DocumentList',
  DOCUMENT_DETAIL: 'DocumentDetail',
  DOCUMENT_UPLOAD: 'DocumentUpload',
  KNOWLEDGE_SEARCH: 'KnowledgeSearch',
  
  // 知识图谱
  KNOWLEDGE_GRAPH: 'KnowledgeGraph',
  ENTITY_MANAGEMENT: 'EntityManagement',
  RELATION_MANAGEMENT: 'RelationManagement',
  GRAPH_ANALYSIS: 'GraphAnalysis',
  
  // 系统管理
  USER_MANAGEMENT: 'UserManagement',
  ROLE_MANAGEMENT: 'RoleManagement',
  SYSTEM_SETTINGS: 'SystemSettings',
  SYSTEM_LOGS: 'SystemLogs',
  
  // 错误页面
  NOT_FOUND: 'NotFound',
  FORBIDDEN: 'Forbidden',
  SERVER_ERROR: 'ServerError'
} as const

// 路由路径常量
export const ROUTE_PATHS = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  NOT_FOUND: '/404',
  FORBIDDEN: '/403',
  SERVER_ERROR: '/500'
} as const

// 创建路由实例
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: routes as RouteRecordRaw[],
  scrollBehavior(to: RouteLocationNormalizedLoaded, from: RouteLocationNormalizedLoaded, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (to.hash) {
      return {
        el: to.hash,
        behavior: 'smooth'
      }
    }
    return { top: 0, behavior: 'smooth' }
  },
  strict: true,
  sensitive: false
})

// 安装路由守卫
setupRouterGuards(router)

// 路由工具函数
export const routerUtils = {
  /**
   * 添加路由
   */
  addRoute: (route: any) => {
    router.addRoute(route)
  },
  
  /**
   * 移除路由
   */
  removeRoute: (name: string) => {
    router.removeRoute(name)
  },
  
  /**
   * 检查路由是否存在
   */
  hasRoute: (name: string) => {
    return router.hasRoute(name)
  },
  
  /**
   * 获取所有路由
   */
  getRoutes: () => {
    return router.getRoutes()
  },
  
  /**
   * 解析路由
   */
  resolve: (to: any) => {
    return router.resolve(to)
  },
  
  /**
   * 导航到指定路由
   */
  push: (to: any) => {
    return router.push(to)
  },
  
  /**
   * 替换当前路由
   */
  replace: (to: any) => {
    return router.replace(to)
  },
  
  /**
   * 前进
   */
  forward: () => {
    return router.forward()
  },
  
  /**
   * 后退
   */
  back: () => {
    return router.back()
  },
  
  /**
   * 跳转指定步数
   */
  go: (delta: number) => {
    return router.go(delta)
  }
}

// 路由跳转辅助函数
export const routeHelpers = {
  /**
   * 跳转到首页
   */
  toHome: () => {
    return router.push(ROUTE_PATHS.HOME)
  },
  
  /**
   * 跳转到登录页
   */
  toLogin: (redirect?: string) => {
    const query = redirect ? { redirect } : {}
    return router.push({ path: ROUTE_PATHS.LOGIN, query })
  },
  
  /**
   * 跳转到仪表板
   */
  toDashboard: () => {
    return router.push(ROUTE_PATHS.DASHBOARD)
  },
  
  /**
   * 跳转到个人中心
   */
  toProfile: () => {
    return router.push(ROUTE_PATHS.PROFILE)
  },
  
  /**
   * 跳转到404页面
   */
  to404: () => {
    return router.push(ROUTE_PATHS.NOT_FOUND)
  },
  
  /**
   * 跳转到403页面
   */
  to403: () => {
    return router.push(ROUTE_PATHS.FORBIDDEN)
  },
  
  /**
   * 跳转到500页面
   */
  to500: () => {
    return router.push(ROUTE_PATHS.SERVER_ERROR)
  },
  
  /**
   * 刷新当前页面
   */
  refresh: () => {
    return router.go(0)
  },
  
  /**
   * 关闭当前标签页并跳转
   */
  closeAndGo: (to: any) => {
    // 这里可以结合标签页管理实现
    return router.replace(to)
  },
  
  /**
   * 在新窗口打开
   */
  openInNewWindow: (to: any) => {
    const resolved = router.resolve(to)
    window.open(resolved.href, '_blank')
  }
}

// 路由状态管理
export const routeState = {
  /**
   * 获取当前路由
   */
  getCurrentRoute: () => {
    return router.currentRoute.value
  },
  
  /**
   * 获取当前路径
   */
  getCurrentPath: () => {
    return router.currentRoute.value.path
  },
  
  /**
   * 获取当前查询参数
   */
  getCurrentQuery: () => {
    return router.currentRoute.value.query
  },
  
  /**
   * 获取当前路由参数
   */
  getCurrentParams: () => {
    return router.currentRoute.value.params
  },
  
  /**
   * 获取当前路由元信息
   */
  getCurrentMeta: () => {
    return router.currentRoute.value.meta
  },
  
  /**
   * 检查当前路由是否匹配
   */
  isCurrentRoute: (name: string) => {
    return router.currentRoute.value.name === name
  },
  
  /**
   * 检查当前路径是否包含
   */
  isCurrentPathContains: (path: string) => {
    return router.currentRoute.value.path.includes(path)
  }
}

// 路由类型守卫
export const routeTypeGuards = {
  /**
   * 检查是否为路由记录
   */
  isRouteRecord: (route: any): route is RouteLocationNormalized => {
    return route && typeof route === 'object' && 'path' in route
  },
  
  /**
   * 检查是否为导航守卫
   */
  isNavigationGuard: (guard: any): guard is NavigationGuardNext => {
    return typeof guard === 'function'
  }
}

// 路由中间件
export const routeMiddleware = {
  /**
   * 认证中间件
   */
  auth: (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    // 认证逻辑
    next()
  },
  
  /**
   * 权限中间件
   */
  permission: (requiredPermissions: string[]) => {
    return (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
      // 权限检查逻辑
      next()
    }
  },
  
  /**
   * 角色中间件
   */
  role: (requiredRoles: string[]) => {
    return (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
      // 角色检查逻辑
      next()
    }
  },
  
  /**
   * 日志中间件
   */
  logger: (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    console.log(`路由跳转: ${from.path} -> ${to.path}`)
    next()
  }
}

export default router