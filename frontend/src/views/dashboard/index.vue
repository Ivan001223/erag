<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">仪表盘</h1>
      <p class="page-description">企业知识图谱系统概览</p>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <el-card class="stat-card" v-for="stat in stats" :key="stat.key">
        <div class="stat-content">
          <div class="stat-icon" :style="{ backgroundColor: stat.color }">
            <el-icon :size="24">
              <component :is="stat.icon" />
            </el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
          <div class="stat-trend" :class="stat.trend">
            <el-icon :size="16">
              <ArrowUp v-if="stat.trend === 'up'" />
              <ArrowDown v-if="stat.trend === 'down'" />
              <Minus v-if="stat.trend === 'stable'" />
            </el-icon>
            <span>{{ stat.change }}</span>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 知识图谱增长趋势 -->
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span>知识图谱增长趋势</span>
            <el-select v-model="chartPeriod" size="small" style="width: 120px">
              <el-option label="最近7天" value="7d" />
              <el-option label="最近30天" value="30d" />
              <el-option label="最近90天" value="90d" />
            </el-select>
          </div>
        </template>
        <div class="chart-container">
          <LineChart :data="growthData" :height="300" />
        </div>
      </el-card>
      
      <!-- 实体类型分布 -->
      <el-card class="chart-card">
        <template #header>
          <span>实体类型分布</span>
        </template>
        <div class="chart-container">
          <PieChart :data="entityTypeData" :height="300" />
        </div>
      </el-card>
    </div>
    
    <!-- 最近活动 -->
    <div class="activity-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>最近活动</span>
            <el-button type="primary" link @click="viewAllActivities">
              查看全部
            </el-button>
          </div>
        </template>
        
        <div class="activity-list">
          <div 
            class="activity-item" 
            v-for="activity in recentActivities" 
            :key="activity.id"
          >
            <div class="activity-icon" :class="activity.type">
              <el-icon>
                <component :is="activity.icon" />
              </el-icon>
            </div>
            <div class="activity-content">
              <div class="activity-title">{{ activity.title }}</div>
              <div class="activity-description">{{ activity.description }}</div>
            </div>
            <div class="activity-time">
              {{ formatTime(activity.createdAt) }}
            </div>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 快速操作 -->
    <div class="quick-actions">
      <el-card>
        <template #header>
          <span>快速操作</span>
        </template>
        
        <div class="actions-grid">
          <div 
            class="action-item" 
            v-for="action in quickActions" 
            :key="action.key"
            @click="handleQuickAction(action)"
          >
            <div class="action-icon" :style="{ backgroundColor: action.color }">
              <el-icon :size="20">
                <component :is="action.icon" />
              </el-icon>
            </div>
            <div class="action-label">{{ action.label }}</div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Document, 
  Share, 
  Search, 
  Plus,
  ArrowUp, 
  ArrowDown, 
  Minus,
  Upload,
  Setting,
  User
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import LineChart from '@/components/charts/LineChart.vue'
import PieChart from '@/components/charts/PieChart.vue'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

// 类型定义
interface StatItem {
  key: string
  label: string
  value: string
  icon: string
  color: string
  trend: 'up' | 'down' | 'stable'
  change: string
}

interface ChartDataset {
  label: string
  data: number[]
  borderColor: string
  backgroundColor: string
}

interface GrowthData {
  labels: string[]
  datasets: ChartDataset[]
}

interface EntityTypeDataset {
  data: number[]
  backgroundColor: string[]
}

interface EntityTypeData {
  labels: string[]
  datasets: EntityTypeDataset[]
}

interface Activity {
  id: number
  type: string
  icon: string
  title: string
  description: string
  createdAt: Date
}

interface QuickAction {
  key: string
  label: string
  icon: string
  color: string
}

const router = useRouter()

// 统计数据
const stats = ref<StatItem[]>([
  {
    key: 'entities',
    label: '实体总数',
    value: '12,345',
    icon: 'Document',
    color: '#409EFF',
    trend: 'up',
    change: '+12%'
  },
  {
    key: 'relations',
    label: '关系总数',
    value: '8,976',
    icon: 'Share',
    color: '#67C23A',
    trend: 'up',
    change: '+8%'
  },
  {
    key: 'documents',
    label: '文档总数',
    value: '2,156',
    icon: 'Document',
    color: '#E6A23C',
    trend: 'stable',
    change: '0%'
  },
  {
    key: 'queries',
    label: '今日查询',
    value: '456',
    icon: 'Search',
    color: '#F56C6C',
    trend: 'down',
    change: '-5%'
  }
])

// 图表时间周期
const chartPeriod = ref<string>('30d')

// 增长趋势数据
const growthData = ref<GrowthData>({
  labels: ['1月', '2月', '3月', '4月', '5月', '6月'],
  datasets: [
    {
      label: '实体数量',
      data: [1200, 1900, 3000, 5000, 8000, 12345],
      borderColor: '#409EFF',
      backgroundColor: 'rgba(64, 158, 255, 0.1)'
    },
    {
      label: '关系数量',
      data: [800, 1200, 2000, 3500, 6000, 8976],
      borderColor: '#67C23A',
      backgroundColor: 'rgba(103, 194, 58, 0.1)'
    }
  ]
})

// 实体类型分布数据
const entityTypeData = ref<EntityTypeData>({
  labels: ['人员', '组织', '产品', '技术', '项目', '其他'],
  datasets: [{
    data: [3245, 2156, 1876, 1543, 1234, 2291],
    backgroundColor: [
      '#409EFF',
      '#67C23A',
      '#E6A23C',
      '#F56C6C',
      '#909399',
      '#C0C4CC'
    ]
  }]
})

// 最近活动
const recentActivities = ref<Activity[]>([
  {
    id: 1,
    type: 'create',
    icon: 'Plus',
    title: '创建新实体',
    description: '用户张三创建了实体"人工智能技术"',
    createdAt: new Date(Date.now() - 1000 * 60 * 30) // 30分钟前
  },
  {
    id: 2,
    type: 'upload',
    icon: 'Upload',
    title: '上传文档',
    description: '用户李四上传了文档"AI发展报告.pdf"',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2) // 2小时前
  },
  {
    id: 3,
    type: 'search',
    icon: 'Search',
    title: '执行查询',
    description: '用户王五查询了"机器学习算法"相关信息',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 4) // 4小时前
  }
])

// 快速操作
const quickActions = ref<QuickAction[]>([
  {
    key: 'create-entity',
    label: '创建实体',
    icon: 'Plus',
    color: '#409EFF'
  },
  {
    key: 'upload-document',
    label: '上传文档',
    icon: 'Upload',
    color: '#67C23A'
  },
  {
    key: 'search-knowledge',
    label: '知识搜索',
    icon: 'Search',
    color: '#E6A23C'
  },
  {
    key: 'manage-users',
    label: '用户管理',
    icon: 'User',
    color: '#F56C6C'
  },
  {
    key: 'system-settings',
    label: '系统设置',
    icon: 'Setting',
    color: '#909399'
  }
])

// 格式化时间
const formatTime = (date: Date) => {
  return formatDistanceToNow(date, { 
    addSuffix: true, 
    locale: zhCN 
  })
}

// 查看全部活动
const viewAllActivities = () => {
  router.push('/system/activities')
}

// 处理快速操作
const handleQuickAction = (action: QuickAction) => {
  switch (action.key) {
    case 'create-entity':
      router.push('/knowledge/entities/create')
      break
    case 'upload-document':
      router.push('/documents/upload')
      break
    case 'search-knowledge':
      router.push('/search')
      break
    case 'manage-users':
      router.push('/system/users')
      break
    case 'system-settings':
      router.push('/system/settings')
      break
    default:
      ElMessage.info('功能开发中...')
  }
}

// 组件挂载时加载数据
onMounted(() => {
  // 这里可以调用API加载真实数据
  console.log('Dashboard mounted')
})
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 0;
}

.page-header {
  margin-bottom: 24px;
  
  .page-title {
    font-size: 24px;
    font-weight: 600;
    margin: 0 0 8px 0;
    color: var(--el-text-color-primary);
  }
  
  .page-description {
    font-size: 14px;
    color: var(--el-text-color-regular);
    margin: 0;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  .stat-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }
  
  .stat-info {
    flex: 1;
    
    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      line-height: 1;
    }
    
    .stat-label {
      font-size: 14px;
      color: var(--el-text-color-regular);
      margin-top: 4px;
    }
  }
  
  .stat-trend {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    
    &.up {
      color: #67C23A;
    }
    
    &.down {
      color: #F56C6C;
    }
    
    &.stable {
      color: var(--el-text-color-regular);
    }
  }
}

.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.chart-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .chart-container {
    padding: 16px 0;
  }
}

.activity-section {
  margin-bottom: 24px;
}

.activity-list {
  .activity-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
    
    &:last-child {
      border-bottom: none;
    }
  }
  
  .activity-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    
    &.create {
      background-color: #409EFF;
    }
    
    &.upload {
      background-color: #67C23A;
    }
    
    &.search {
      background-color: #E6A23C;
    }
  }
  
  .activity-content {
    flex: 1;
    
    .activity-title {
      font-weight: 500;
      color: var(--el-text-color-primary);
      margin-bottom: 4px;
    }
    
    .activity-description {
      font-size: 14px;
      color: var(--el-text-color-regular);
    }
  }
  
  .activity-time {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

.quick-actions {
  .actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 16px;
  }
  
  .action-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;
    
    &:hover {
      background-color: var(--el-fill-color-light);
      transform: translateY(-2px);
    }
  }
  
  .action-icon {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }
  
  .action-label {
    font-size: 14px;
    color: var(--el-text-color-primary);
    text-align: center;
  }
}

// 响应式设计
@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .actions-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>