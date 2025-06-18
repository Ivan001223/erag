<template>
  <div class="app-sidebar" :class="{ 'sidebar-collapsed': collapsed }">
    <!-- Logo区域 -->
    <div class="sidebar-logo">
      <div class="logo-container">
        <img src="/logo.svg" alt="ERAG" class="logo-image" />
        <transition name="fade">
          <span v-show="!collapsed" class="logo-text">ERAG</span>
        </transition>
      </div>
    </div>
    
    <!-- 导航菜单 -->
    <el-scrollbar class="sidebar-scrollbar">
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        :unique-opened="true"
        :router="true"
        class="sidebar-menu"
      >
        <!-- 仪表盘 -->
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        
        <!-- 知识图谱 -->
        <el-sub-menu index="knowledge">
          <template #title>
            <el-icon><Share /></el-icon>
            <span>知识图谱</span>
          </template>
          <el-menu-item index="/knowledge/graphs">
            <el-icon><Grid /></el-icon>
            <template #title>图谱管理</template>
          </el-menu-item>
          <el-menu-item index="/knowledge/entities">
            <el-icon><Document /></el-icon>
            <template #title>实体管理</template>
          </el-menu-item>
          <el-menu-item index="/knowledge/relations">
            <el-icon><Connection /></el-icon>
            <template #title>关系管理</template>
          </el-menu-item>
        </el-sub-menu>
        
        <!-- 文档管理 -->
        <el-sub-menu index="documents">
          <template #title>
            <el-icon><Folder /></el-icon>
            <span>文档管理</span>
          </template>
          <el-menu-item index="/documents/list">
            <el-icon><Document /></el-icon>
            <template #title>文档列表</template>
          </el-menu-item>
          <el-menu-item index="/documents/upload">
            <el-icon><Upload /></el-icon>
            <template #title>文档上传</template>
          </el-menu-item>
          <el-menu-item index="/documents/categories">
            <el-icon><Collection /></el-icon>
            <template #title>分类管理</template>
          </el-menu-item>
        </el-sub-menu>
        
        <!-- 智能搜索 -->
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <template #title>智能搜索</template>
        </el-menu-item>
        
        <!-- 数据分析 -->
        <el-sub-menu index="analytics">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>数据分析</span>
          </template>
          <el-menu-item index="/analytics/overview">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>数据概览</template>
          </el-menu-item>
          <el-menu-item index="/analytics/reports">
            <el-icon><Document /></el-icon>
            <template #title>分析报告</template>
          </el-menu-item>
        </el-sub-menu>
        
        <!-- 系统管理 -->
        <el-sub-menu index="system" v-if="hasSystemPermission">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/system/users">
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
          <el-menu-item index="/system/roles">
            <el-icon><UserFilled /></el-icon>
            <template #title>角色管理</template>
          </el-menu-item>
          <el-menu-item index="/system/permissions">
            <el-icon><Key /></el-icon>
            <template #title>权限管理</template>
          </el-menu-item>
          <el-menu-item index="/system/settings">
            <el-icon><Tools /></el-icon>
            <template #title>系统设置</template>
          </el-menu-item>
          <el-menu-item index="/system/logs">
            <el-icon><Document /></el-icon>
            <template #title>系统日志</template>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-scrollbar>
    
    <!-- 底部折叠按钮 -->
    <div class="sidebar-footer">
      <el-button 
        class="collapse-btn"
        @click="toggleCollapse"
        circle
      >
        <el-icon>
          <Expand v-if="collapsed" />
          <Fold v-else />
        </el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  Odometer, Share, Grid, Document, Connection, Folder, Upload, Collection,
  Search, TrendCharts, DataAnalysis, Setting, User, UserFilled, Key, Tools,
  Expand, Fold
} from '@element-plus/icons-vue'

interface Props {
  collapsed: boolean
}

interface Emits {
  (e: 'update:collapsed', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const route = useRoute()
const userStore = useUserStore()

// 当前激活的菜单
const activeMenu = computed(() => {
  return route.path
})

// 是否有系统管理权限
const hasSystemPermission = computed(() => {
  return userStore.hasPermission('system:manage')
})

// 切换折叠状态
const toggleCollapse = () => {
  emit('update:collapsed', !props.collapsed)
}
</script>

<style lang="scss" scoped>
.app-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 240px;
  height: 100vh;
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  z-index: 1000;
  
  &.sidebar-collapsed {
    width: 64px;
  }
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color-light);
  
  .logo-container {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .logo-image {
      width: 32px;
      height: 32px;
      flex-shrink: 0;
    }
    
    .logo-text {
      font-size: 20px;
      font-weight: 600;
      color: var(--el-color-primary);
      white-space: nowrap;
    }
  }
}

.sidebar-scrollbar {
  flex: 1;
  
  :deep(.el-scrollbar__view) {
    height: 100%;
  }
}

.sidebar-menu {
  border: none;
  height: 100%;
  
  :deep(.el-menu-item) {
    height: 48px;
    line-height: 48px;
    
    &.is-active {
      background-color: var(--el-color-primary-light-9);
      color: var(--el-color-primary);
      
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background-color: var(--el-color-primary);
      }
    }
    
    &:hover {
      background-color: var(--el-fill-color-light);
    }
  }
  
  :deep(.el-sub-menu__title) {
    height: 48px;
    line-height: 48px;
    
    &:hover {
      background-color: var(--el-fill-color-light);
    }
  }
  
  :deep(.el-sub-menu .el-menu-item) {
    height: 40px;
    line-height: 40px;
    padding-left: 52px !important;
    
    &.is-active {
      background-color: var(--el-color-primary-light-9);
      color: var(--el-color-primary);
    }
  }
}

.sidebar-footer {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid var(--el-border-color-light);
  
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
}

// 折叠状态下的样式调整
.sidebar-collapsed {
  .sidebar-menu {
    :deep(.el-sub-menu .el-menu-item) {
      padding-left: 20px !important;
    }
  }
}

// 动画效果
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// 响应式设计
@media (max-width: 768px) {
  .app-sidebar {
    transform: translateX(-100%);
    
    &.sidebar-show {
      transform: translateX(0);
    }
  }
}
</style>