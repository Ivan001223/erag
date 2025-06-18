<template>
  <div class="app-breadcrumb">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item 
        v-for="(item, index) in breadcrumbList" 
        :key="item.path"
        :to="item.path && index < breadcrumbList.length - 1 ? item.path : undefined"
      >
        <el-icon v-if="item.icon" class="breadcrumb-icon">
          <component :is="item.icon" />
        </el-icon>
        <span>{{ item.title }}</span>
      </el-breadcrumb-item>
    </el-breadcrumb>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  House, DataBoard, Share, Document, Search, 
  DataAnalysis, Setting, User, Files
} from '@element-plus/icons-vue'

interface BreadcrumbItem {
  title: string
  path?: string
  icon?: string
}

const route = useRoute()
const router = useRouter()

// 路由图标映射
const routeIconMap: Record<string, string> = {
  '/dashboard': 'House',
  '/knowledge': 'Share',
  '/knowledge/graphs': 'Share',
  '/knowledge/entities': 'Document',
  '/knowledge/relations': 'Files',
  '/documents': 'Document',
  '/search': 'Search',
  '/analytics': 'DataAnalysis',
  '/system': 'Setting',
  '/profile': 'User',
  '/settings': 'Setting'
}

// 路由标题映射
const routeTitleMap: Record<string, string> = {
  '/': '首页',
  '/dashboard': '仪表盘',
  '/knowledge': '知识图谱',
  '/knowledge/graphs': '图谱管理',
  '/knowledge/graphs/create': '创建图谱',
  '/knowledge/graphs/:id': '图谱详情',
  '/knowledge/graphs/:id/edit': '编辑图谱',
  '/knowledge/entities': '实体管理',
  '/knowledge/entities/create': '创建实体',
  '/knowledge/entities/:id': '实体详情',
  '/knowledge/entities/:id/edit': '编辑实体',
  '/knowledge/relations': '关系管理',
  '/knowledge/relations/create': '创建关系',
  '/knowledge/relations/:id': '关系详情',
  '/documents': '文档管理',
  '/documents/upload': '上传文档',
  '/documents/:id': '文档详情',
  '/search': '智能搜索',
  '/analytics': '数据分析',
  '/analytics/overview': '概览',
  '/analytics/reports': '报表',
  '/system': '系统管理',
  '/system/users': '用户管理',
  '/system/roles': '角色管理',
  '/system/permissions': '权限管理',
  '/system/settings': '系统设置',
  '/profile': '个人资料',
  '/settings': '账户设置',
  '/help': '帮助中心',
  '/notifications': '通知中心'
}

// 生成面包屑列表
const breadcrumbList = computed<BreadcrumbItem[]>(() => {
  const pathArray = route.path.split('/').filter(path => path)
  const breadcrumbs: BreadcrumbItem[] = []
  
  // 添加首页
  breadcrumbs.push({
    title: '首页',
    path: '/dashboard',
    icon: 'House'
  })
  
  // 如果当前就是首页，直接返回
  if (route.path === '/dashboard' || route.path === '/') {
    return breadcrumbs
  }
  
  // 构建路径面包屑
  let currentPath = ''
  
  pathArray.forEach((path, index) => {
    currentPath += `/${path}`
    
    // 获取路由标题
    let title = routeTitleMap[currentPath] || path
    
    // 处理动态路由参数
    if (title.includes(':')) {
      const paramKey = title.split(':')[1]
      const paramValue = route.params[paramKey]
      if (paramValue) {
        // 根据参数类型设置不同的标题格式
        if (paramKey === 'id') {
          title = `详情 (${paramValue})`
        } else {
          title = String(paramValue)
        }
      }
    }
    
    // 处理特殊的路由标题
    if (route.meta?.title) {
      title = route.meta.title as string
    }
    
    // 获取图标
    const icon = routeIconMap[currentPath] || getIconByPath(currentPath)
    
    breadcrumbs.push({
      title,
      path: index === pathArray.length - 1 ? undefined : currentPath, // 最后一项不可点击
      icon
    })
  })
  
  return breadcrumbs
})

// 根据路径获取图标
const getIconByPath = (path: string): string => {
  if (path.includes('/graphs')) return 'Share'
  if (path.includes('/entities')) return 'Document'
  if (path.includes('/relations')) return 'Files'
  if (path.includes('/documents')) return 'Document'
  if (path.includes('/search')) return 'Search'
  if (path.includes('/analytics')) return 'DataAnalysis'
  if (path.includes('/system')) return 'Setting'
  if (path.includes('/profile')) return 'User'
  if (path.includes('/settings')) return 'Setting'
  return 'Document'
}
</script>

<style lang="scss" scoped>
.app-breadcrumb {
  padding: 0 16px;
  height: 100%;
  display: flex;
  align-items: center;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-lighter);
  
  :deep(.el-breadcrumb) {
    font-size: 14px;
    
    .el-breadcrumb__item {
      .el-breadcrumb__inner {
        display: flex;
        align-items: center;
        gap: 4px;
        color: var(--el-text-color-regular);
        font-weight: 400;
        
        &:hover {
          color: var(--el-color-primary);
        }
        
        &.is-link {
          color: var(--el-text-color-primary);
          
          &:hover {
            color: var(--el-color-primary);
          }
        }
      }
      
      &:last-child {
        .el-breadcrumb__inner {
          color: var(--el-text-color-primary);
          font-weight: 500;
          cursor: default;
          
          &:hover {
            color: var(--el-text-color-primary);
          }
        }
      }
      
      .el-breadcrumb__separator {
        color: var(--el-text-color-placeholder);
        margin: 0 8px;
      }
    }
  }
}

.breadcrumb-icon {
  font-size: 14px;
}

// 响应式设计
@media (max-width: 768px) {
  .app-breadcrumb {
    padding: 0 12px;
    
    :deep(.el-breadcrumb) {
      font-size: 13px;
      
      .el-breadcrumb__item {
        .el-breadcrumb__separator {
          margin: 0 6px;
        }
      }
    }
  }
  
  .breadcrumb-icon {
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .app-breadcrumb {
    padding: 0 8px;
    
    :deep(.el-breadcrumb) {
      font-size: 12px;
      
      // 在小屏幕上隐藏中间的面包屑项，只显示首页和当前页
      .el-breadcrumb__item {
        &:not(:first-child):not(:last-child) {
          display: none;
        }
        
        &:first-child + .el-breadcrumb__item:not(:last-child) {
          &::before {
            content: '...';
            color: var(--el-text-color-placeholder);
            margin: 0 6px;
          }
          
          .el-breadcrumb__inner {
            display: none;
          }
          
          .el-breadcrumb__separator {
            display: none;
          }
        }
      }
    }
  }
}
</style>