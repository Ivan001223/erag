import type {
  RouteRecordRaw,
  RouteRecordSingleView,
  RouteRecordMultipleViews,
  RouteRecordRedirect
} from 'vue-router'
import type { Component } from 'vue'

/**
 * 路由元信息接口
 */
export interface RouteMeta {
  /** 页面标题 */
  title?: string
  /** 页面图标 */
  icon?: string
  /** 是否需要认证 */
  requiresAuth?: boolean
  /** 所需权限 */
  permissions?: string[]
  /** 所需角色 */
  roles?: string[]
  /** 是否在菜单中隐藏 */
  hidden?: boolean
  /** 是否固定在标签页 */
  affix?: boolean
  /** 是否缓存页面 */
  keepAlive?: boolean
  /** 面包屑导航 */
  breadcrumb?: boolean
  /** 页面布局 */
  layout?: 'default' | 'blank' | 'auth'
  /** 重定向地址 */
  redirect?: string
  /** 外部链接 */
  externalLink?: string
  /** 排序权重 */
  sort?: number
  /** 页面描述 */
  description?: string
  /** 页面关键词 */
  keywords?: string[]
  /** 是否为新窗口打开 */
  target?: '_blank' | '_self'
  /** 菜单分组 */
  group?: string
  /** 是否为开发环境专用 */
  devOnly?: boolean
}

/**
 * 扩展路由记录类型
 */
export type AppRouteRecordRaw =
  | (Omit<RouteRecordSingleView, 'meta' | 'children'> & { meta?: RouteMeta; children?: AppRouteRecordRaw[] })
  | (Omit<RouteRecordMultipleViews, 'meta' | 'children'> & { meta?: RouteMeta; children?: AppRouteRecordRaw[] })
  | (Omit<RouteRecordRedirect, 'meta' | 'children'> & { meta?: RouteMeta; children?: AppRouteRecordRaw[] })

/**
 * 布局组件
 */
const Layout = () => import('../layouts/default/index.vue')
const BlankLayout = () => import('../layouts/blank/index.vue')
const AuthLayout = () => import('../layouts/auth/index.vue')

/**
 * 基础路由（不需要权限）
 */
export const basicRoutes: AppRouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/auth/login/index.vue'),
    meta: {
      title: '登录',
      layout: 'auth',
      hidden: true
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/auth/register/index.vue'),
    meta: {
      title: '注册',
      layout: 'auth',
      hidden: true
    }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/auth/forgot-password/index.vue'),
    meta: {
      title: '忘记密码',
      layout: 'auth',
      hidden: true
    }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../views/auth/reset-password/index.vue'),
    meta: {
      title: '重置密码',
      layout: 'auth',
      hidden: true
    }
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('../views/error/404.vue'),
    meta: {
      title: '页面不存在',
      layout: 'blank',
      hidden: true
    }
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('../views/error/403.vue'),
    meta: {
      title: '权限不足',
      layout: 'blank',
      hidden: true
    }
  },
  {
    path: '/500',
    name: 'ServerError',
    component: () => import('../views/error/500.vue'),
    meta: {
      title: '服务器错误',
      layout: 'blank',
      hidden: true
    }
  }
]

/**
 * 主要路由（需要权限）
 */
export const mainRoutes: AppRouteRecordRaw[] = [
  {
    path: '/',
    name: 'Root',
    component: Layout,
    meta: {
      title: '首页',
      hidden: true
    },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/dashboard/index.vue'),
        meta: {
          title: '仪表盘',
          icon: 'dashboard',
          requiresAuth: true,
          affix: true,
          sort: 1
        }
      }
    ]
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: Layout,
    meta: {
      title: '知识图谱',
      icon: 'knowledge',
      requiresAuth: true,
      sort: 2
    },
    children: [
      {
        path: 'graphs',
        name: 'KnowledgeGraphs',
        component: () => import('../views/knowledge/graphs/index.vue'),
        meta: {
          title: '图谱管理',
          icon: 'graph',
          requiresAuth: true,
          permissions: ['knowledge:graph:read']
        }
      },
      {
        path: 'graphs/create',
        name: 'CreateKnowledgeGraph',
        component: () => import('../views/knowledge/graphs/create.vue'),
        meta: {
          title: '创建图谱',
          requiresAuth: true,
          permissions: ['knowledge:graph:create'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'graphs/:id',
        name: 'KnowledgeGraphDetail',
        component: () => import('../views/knowledge/graphs/detail.vue'),
        meta: {
          title: '图谱详情',
          requiresAuth: true,
          permissions: ['knowledge:graph:read'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'graphs/:id/edit',
        name: 'EditKnowledgeGraph',
        component: () => import('../views/knowledge/graphs/edit.vue'),
        meta: {
          title: '编辑图谱',
          requiresAuth: true,
          permissions: ['knowledge:graph:update'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'entities',
        name: 'Entities',
        component: () => import('../views/knowledge/entities/index.vue'),
        meta: {
          title: '实体管理',
          icon: 'entity',
          requiresAuth: true,
          permissions: ['knowledge:entity:read']
        }
      },
      {
        path: 'entities/create',
        name: 'CreateEntity',
        component: () => import('../views/knowledge/entities/create.vue'),
        meta: {
          title: '创建实体',
          requiresAuth: true,
          permissions: ['knowledge:entity:create'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'entities/:id',
        name: 'EntityDetail',
        component: () => import('../views/knowledge/entities/detail.vue'),
        meta: {
          title: '实体详情',
          requiresAuth: true,
          permissions: ['knowledge:entity:read'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'entities/:id/edit',
        name: 'EditEntity',
        component: () => import('../views/knowledge/entities/edit.vue'),
        meta: {
          title: '编辑实体',
          requiresAuth: true,
          permissions: ['knowledge:entity:update'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'relations',
        name: 'Relations',
        component: () => import('../views/knowledge/relations/index.vue'),
        meta: {
          title: '关系管理',
          icon: 'relation',
          requiresAuth: true,
          permissions: ['knowledge:relation:read']
        }
      },
      {
        path: 'relations/create',
        name: 'CreateRelation',
        component: () => import('../views/knowledge/relations/create.vue'),
        meta: {
          title: '创建关系',
          requiresAuth: true,
          permissions: ['knowledge:relation:create'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'relations/:id',
        name: 'RelationDetail',
        component: () => import('../views/knowledge/relations/detail.vue'),
        meta: {
          title: '关系详情',
          requiresAuth: true,
          permissions: ['knowledge:relation:read'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'relations/:id/edit',
        name: 'EditRelation',
        component: () => import('../views/knowledge/relations/edit.vue'),
        meta: {
          title: '编辑关系',
          requiresAuth: true,
          permissions: ['knowledge:relation:update'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('../views/knowledge/documents/index.vue'),
        meta: {
          title: '文档管理',
          icon: 'document',
          requiresAuth: true,
          permissions: ['knowledge:document:read']
        }
      },
      {
        path: 'documents/upload',
        name: 'UploadDocument',
        component: () => import('../views/knowledge/documents/upload.vue'),
        meta: {
          title: '上传文档',
          requiresAuth: true,
          permissions: ['knowledge:document:create'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('../views/knowledge/documents/detail.vue'),
        meta: {
          title: '文档详情',
          requiresAuth: true,
          permissions: ['knowledge:document:read'],
          hidden: true,
          breadcrumb: true
        }
      },
      {
        path: 'search',
        name: 'KnowledgeSearch',
        component: () => import('../views/knowledge/search/index.vue'),
        meta: {
          title: '知识搜索',
          icon: 'search',
          requiresAuth: true,
          permissions: ['knowledge:search']
        }
      },
      {
        path: 'etl',
        name: 'KnowledgeETL',
        component: () => import('../views/knowledge/etl/index.vue'),
        meta: {
          title: 'ETL作业监控',
          icon: 'Monitor',
          requiresAuth: true
        }
      },
      {
        path: 'analysis',
        name: 'KnowledgeAnalysis',
        component: () => import('../views/knowledge/analysis/index.vue'),
        meta: {
          title: '图谱分析',
          icon: 'analysis',
          requiresAuth: true,
          permissions: ['knowledge:analysis']
        }
      }
    ]
  },
  {
    path: '/user',
    name: 'User',
    component: Layout,
    meta: {
      title: '用户管理',
      icon: 'user',
      requiresAuth: true,
      permissions: ['user:read'],
      sort: 3
    },
    children: [
      {
        path: 'list',
        name: 'UserList',
        component: () => import('../views/user/list/index.vue'),
        meta: {
          title: '用户列表',
          icon: 'user-list',
          requiresAuth: true,
          permissions: ['user:read']
        }
      },
      {
        path: 'roles',
        name: 'UserRoles',
        component: () => import('../views/user/roles/index.vue'),
        meta: {
          title: '角色管理',
          icon: 'role',
          requiresAuth: true,
          permissions: ['user:role:read']
        }
      },
      {
        path: 'permissions',
        name: 'UserPermissions',
        component: () => import('../views/user/permissions/index.vue'),
        meta: {
          title: '权限管理',
          icon: 'permission',
          requiresAuth: true,
          permissions: ['user:permission:read']
        }
      },
      {
        path: 'departments',
        name: 'UserDepartments',
        component: () => import('../views/user/departments/index.vue'),
        meta: {
          title: '部门管理',
          icon: 'department',
          requiresAuth: true,
          permissions: ['user:department:read']
        }
      }
    ]
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Layout,
    meta: {
      title: '个人中心',
      hidden: true,
      requiresAuth: true
    },
    children: [
      {
        path: '',
        name: 'UserProfile',
        component: () => import('../views/profile/index.vue'),
        meta: {
          title: '个人信息',
          requiresAuth: true,
          breadcrumb: false
        }
      },
      {
        path: 'settings',
        name: 'ProfileSettings',
        component: () => import('../views/profile/settings.vue'),
        meta: {
          title: '个人设置',
          requiresAuth: true,
          breadcrumb: true
        }
      },
      {
        path: 'security',
        name: 'ProfileSecurity',
        component: () => import('../views/profile/security.vue'),
        meta: {
          title: '安全设置',
          requiresAuth: true,
          breadcrumb: true
        }
      }
    ]
  },
  {
    path: '/system',
    name: 'System',
    component: Layout,
    meta: {
      title: '系统管理',
      icon: 'system',
      requiresAuth: true,
      permissions: ['system:read'],
      roles: ['admin'],
      sort: 4
    },
    children: [
      {
        path: 'settings',
        name: 'SystemSettings',
        component: () => import('../views/system/settings/index.vue'),
        meta: {
          title: '系统设置',
          icon: 'settings',
          requiresAuth: true,
          permissions: ['system:settings:read']
        }
      },
      {
        path: 'logs',
        name: 'SystemLogs',
        component: () => import('../views/system/logs/index.vue'),
        meta: {
          title: '系统日志',
          icon: 'logs',
          requiresAuth: true,
          permissions: ['system:logs:read']
        }
      },
      {
        path: 'monitoring',
        name: 'SystemMonitoring',
        component: () => import('../views/system/monitoring/index.vue'),
        meta: {
          title: '系统监控',
          icon: 'monitoring',
          requiresAuth: true,
          permissions: ['system:monitoring:read']
        }
      },
      {
        path: 'backup',
        name: 'SystemBackup',
        component: () => import('../views/system/backup/index.vue'),
        meta: {
          title: '数据备份',
          icon: 'backup',
          requiresAuth: true,
          permissions: ['system:backup:read']
        }
      }
    ]
  }
]

/**
 * 开发环境路由
 */
export const devRoutes: AppRouteRecordRaw[] = [
  {
    path: '/dev',
    name: 'Development',
    component: Layout,
    meta: {
      title: '开发工具',
      icon: 'dev',
      requiresAuth: true,
      devOnly: true,
      sort: 999
    },
    children: [
      {
        path: 'components',
        name: 'DevComponents',
        component: () => import('../views/dev/components/index.vue'),
        meta: {
          title: '组件示例',
          icon: 'component',
          requiresAuth: true,
          devOnly: true
        }
      },
      {
        path: 'icons',
        name: 'DevIcons',
        component: () => import('../views/dev/icons/index.vue'),
        meta: {
          title: '图标库',
          icon: 'icon',
          requiresAuth: true,
          devOnly: true
        }
      },
      {
        path: 'api-test',
        name: 'DevApiTest',
        component: () => import('../views/dev/api-test/index.vue'),
        meta: {
          title: 'API 测试',
          icon: 'api',
          requiresAuth: true,
          devOnly: true
        }
      }
    ]
  }
]

/**
 * 外部链接路由
 */
export const externalRoutes: AppRouteRecordRaw[] = [
  {
    path: '/external',
    name: 'External',
    component: Layout,
    meta: {
      title: '外部链接',
      icon: 'external',
      sort: 5
    },
    children: [
      {
        path: 'github',
        name: 'GitHub',
        component: () => import('../views/external/redirect.vue'),
        meta: {
          title: 'GitHub',
          icon: 'github',
          externalLink: 'https://github.com',
          target: '_blank'
        }
      },
      {
        path: 'documentation',
        name: 'Documentation',
        component: () => import('../views/external/redirect.vue'),
        meta: {
          title: '项目文档',
          icon: 'documentation',
          externalLink: 'https://docs.example.com',
          target: '_blank'
        }
      }
    ]
  }
]

/**
 * 所有路由
 */
export const routes: AppRouteRecordRaw[] = [
  ...basicRoutes,
  ...mainRoutes,
  ...(process.env.NODE_ENV === 'development' ? devRoutes : []),
  ...externalRoutes,
  {
    // 404 路由必须放在最后
    path: '/:pathMatch(.*)*',
    name: 'NotFoundRedirect',
    redirect: '/404',
    meta: {
      hidden: true
    }
  }
]

/**
 * 获取路由菜单
 * @param routes 路由配置
 * @param permissions 用户权限
 * @param roles 用户角色
 * @returns 过滤后的菜单路由
 */
export const getMenuRoutes = (
  routes: AppRouteRecordRaw[],
  permissions: string[] = [],
  roles: string[] = []
): AppRouteRecordRaw[] => {
  return routes
    .filter(route => {
      const meta = route.meta || {}
      
      // 过滤隐藏的路由
      if (meta.hidden) return false
      
      // 过滤开发环境专用路由
      if (meta.devOnly && process.env.NODE_ENV !== 'development') return false
      
      // 检查权限
      if (meta.permissions && meta.permissions.length > 0) {
        if (!meta.permissions.some(permission => permissions.includes(permission))) {
          return false
        }
      }
      
      // 检查角色
      if (meta.roles && meta.roles.length > 0) {
        if (!meta.roles.some(role => roles.includes(role))) {
          return false
        }
      }
      
      return true
    })
    .map(route => {
      if (route.children && route.children.length > 0) {
        return {
          ...route,
          children: getMenuRoutes(route.children, permissions, roles)
        }
      }
      return route
    })
    .filter(route => {
      // 如果父路由没有子路由，且自身也不是菜单项，则过滤掉
      if (route.children && route.children.length === 0 && route.meta?.hidden !== false) {
        return false
      }
      return true
    })
    .sort((a, b) => {
      const sortA = a.meta?.sort || 999
      const sortB = b.meta?.sort || 999
      return sortA - sortB
    })
}

/**
 * 获取面包屑导航
 * @param route 当前路由
 * @param routes 所有路由
 * @returns 面包屑数组
 */
export const getBreadcrumbs = (
  route: any,
  routes: AppRouteRecordRaw[]
): Array<{ title: string; path?: string }> => {
  const breadcrumbs: Array<{ title: string; path?: string }> = []
  
  const findRoute = (routes: AppRouteRecordRaw[], path: string): AppRouteRecordRaw | null => {
    for (const r of routes) {
      if (r.path === path) return r
      if (r.children) {
        const found = findRoute(r.children, path)
        if (found) return found
      }
    }
    return null
  }
  
  const pathSegments = route.path.split('/').filter(Boolean)
  let currentPath = ''
  
  for (const segment of pathSegments) {
    currentPath += `/${segment}`
    const foundRoute = findRoute(routes, currentPath)
    
    if (foundRoute && foundRoute.meta?.title) {
      breadcrumbs.push({
        title: foundRoute.meta.title,
        path: foundRoute.meta.breadcrumb !== false ? currentPath : undefined
      })
    }
  }
  
  return breadcrumbs
}

export default routes