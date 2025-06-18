<template>
  <div class="knowledge-analysis">
    <!-- 页面头部 -->
    <div class="analysis-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="page-title">
            <el-icon><TrendCharts /></el-icon>
            知识分析
          </h1>
          <p class="page-description">
            深入分析知识库内容，提供数据洞察和智能建议
          </p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="refreshAnalysis">
            <el-icon><Refresh /></el-icon>
            刷新分析
          </el-button>
          <el-button @click="exportReport">
            <el-icon><Download /></el-icon>
            导出报告
          </el-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="6" v-for="stat in stats" :key="stat.key">
          <div class="stat-card">
            <div class="stat-icon" :style="{ backgroundColor: stat.color }">
              <el-icon :size="24">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
              <div class="stat-change" :class="stat.trend">
                <el-icon><component :is="stat.trendIcon" /></el-icon>
                {{ stat.change }}
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 分析内容 -->
    <div class="analysis-content">
      <el-row :gutter="20">
        <!-- 左侧图表区域 -->
        <el-col :xs="24" :lg="16">
          <!-- 知识分布图表 -->
          <el-card class="chart-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="card-title">
                  <el-icon><PieChart /></el-icon>
                  知识分布分析
                </span>
                <el-select v-model="distributionType" size="small" style="width: 120px">
                  <el-option label="按类型" value="type" />
                  <el-option label="按标签" value="tag" />
                  <el-option label="按来源" value="source" />
                </el-select>
              </div>
            </template>
            <div class="chart-container">
              <div ref="distributionChart" class="chart"></div>
            </div>
          </el-card>

          <!-- 趋势分析图表 -->
          <el-card class="chart-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="card-title">
                  <el-icon><LineChart /></el-icon>
                  知识增长趋势
                </span>
                <el-select v-model="trendPeriod" size="small" style="width: 120px">
                  <el-option label="最近7天" value="7d" />
                  <el-option label="最近30天" value="30d" />
                  <el-option label="最近90天" value="90d" />
                </el-select>
              </div>
            </template>
            <div class="chart-container">
              <div ref="trendChart" class="chart"></div>
            </div>
          </el-card>

          <!-- 热门内容分析 -->
          <el-card class="chart-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="card-title">
                  <el-icon><Histogram /></el-icon>
                  热门内容分析
                </span>
                <el-radio-group v-model="hotContentType" size="small">
                  <el-radio-button label="view">访问量</el-radio-button>
                  <el-radio-button label="search">搜索量</el-radio-button>
                  <el-radio-button label="rating">评分</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div class="chart-container">
              <div ref="hotContentChart" class="chart"></div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧信息面板 -->
        <el-col :xs="24" :lg="8">
          <!-- 质量评估 -->
          <el-card class="info-card" shadow="hover">
            <template #header>
              <span class="card-title">
                <el-icon><Medal /></el-icon>
                质量评估
              </span>
            </template>
            <div class="quality-assessment">
              <div class="quality-item" v-for="quality in qualityMetrics" :key="quality.name">
                <div class="quality-header">
                  <span class="quality-name">{{ quality.name }}</span>
                  <span class="quality-score" :class="getScoreClass(quality.score)">
                    {{ quality.score }}/100
                  </span>
                </div>
                <el-progress 
                  :percentage="quality.score" 
                  :color="getProgressColor(quality.score)"
                  :show-text="false"
                  :stroke-width="8"
                />
                <div class="quality-description">{{ quality.description }}</div>
              </div>
            </div>
          </el-card>

          <!-- 智能建议 -->
          <el-card class="info-card" shadow="hover">
            <template #header>
              <span class="card-title">
                <el-icon><Lightbulb /></el-icon>
                智能建议
              </span>
            </template>
            <div class="suggestions">
              <div class="suggestion-item" v-for="suggestion in suggestions" :key="suggestion.id">
                <div class="suggestion-header">
                  <el-icon class="suggestion-icon" :class="suggestion.type">
                    <component :is="suggestion.icon" />
                  </el-icon>
                  <span class="suggestion-title">{{ suggestion.title }}</span>
                  <el-tag :type="suggestion.priority" size="small">{{ suggestion.priorityText }}</el-tag>
                </div>
                <div class="suggestion-content">{{ suggestion.content }}</div>
                <div class="suggestion-actions">
                  <el-button size="small" text @click="applySuggestion(suggestion)">
                    应用建议
                  </el-button>
                  <el-button size="small" text @click="ignoreSuggestion(suggestion)">
                    忽略
                  </el-button>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 最近活动 -->
          <el-card class="info-card" shadow="hover">
            <template #header>
              <span class="card-title">
                <el-icon><Clock /></el-icon>
                最近活动
              </span>
            </template>
            <div class="recent-activities">
              <div class="activity-item" v-for="activity in recentActivities" :key="activity.id">
                <div class="activity-icon">
                  <el-icon :class="activity.type">
                    <component :is="activity.icon" />
                  </el-icon>
                </div>
                <div class="activity-content">
                  <div class="activity-title">{{ activity.title }}</div>
                  <div class="activity-description">{{ activity.description }}</div>
                  <div class="activity-time">{{ activity.time }}</div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  TrendCharts,
  Refresh,
  Download,
  PieChart,
  DataLine as LineChart,
  Histogram,
  Medal,
  Opportunity as Lightbulb,
  Clock,
  Document,
  User,
  View,
  Search,
  ArrowUp,
  ArrowDown,
  Warning,
  InfoFilled,
  SuccessFilled,
  Plus,
  Edit,
  Delete
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'

// 图表实例
let distributionChartInstance: echarts.ECharts | null = null
let trendChartInstance: echarts.ECharts | null = null
let hotContentChartInstance: echarts.ECharts | null = null

// 图表DOM引用
const distributionChart = ref<HTMLElement>()
const trendChart = ref<HTMLElement>()
const hotContentChart = ref<HTMLElement>()

// 响应式数据
const distributionType = ref('type')
const trendPeriod = ref('30d')
const hotContentType = ref('view')

// 统计数据
const stats = reactive([
  {
    key: 'total',
    label: '总知识条目',
    value: '2,847',
    change: '+12.5%',
    trend: 'up',
    trendIcon: 'ArrowUp',
    icon: 'Document',
    color: '#409eff'
  },
  {
    key: 'users',
    label: '活跃用户',
    value: '1,234',
    change: '+8.3%',
    trend: 'up',
    trendIcon: 'ArrowUp',
    icon: 'User',
    color: '#67c23a'
  },
  {
    key: 'views',
    label: '总访问量',
    value: '45.2K',
    change: '+15.7%',
    trend: 'up',
    trendIcon: 'ArrowUp',
    icon: 'View',
    color: '#e6a23c'
  },
  {
    key: 'searches',
    label: '搜索次数',
    value: '8,956',
    change: '-2.1%',
    trend: 'down',
    trendIcon: 'ArrowDown',
    icon: 'Search',
    color: '#f56c6c'
  }
])

// 质量评估指标
const qualityMetrics = reactive([
  {
    name: '内容完整性',
    score: 85,
    description: '大部分内容结构完整，信息充实'
  },
  {
    name: '准确性',
    score: 92,
    description: '内容准确度高，错误率低'
  },
  {
    name: '时效性',
    score: 78,
    description: '部分内容需要更新，建议定期维护'
  },
  {
    name: '可读性',
    score: 88,
    description: '内容表达清晰，易于理解'
  }
])

// 智能建议
const suggestions = reactive([
  {
    id: 1,
    title: '优化搜索关键词',
    content: '建议为热门内容添加更多相关关键词，提高搜索命中率',
    type: 'info',
    priority: 'warning',
    priorityText: '中等',
    icon: 'InfoFilled'
  },
  {
    id: 2,
    title: '更新过期内容',
    content: '发现23条内容超过6个月未更新，建议及时维护',
    type: 'warning',
    priority: 'danger',
    priorityText: '高',
    icon: 'Warning'
  },
  {
    id: 3,
    title: '扩充薄弱领域',
    content: '技术文档类别内容相对较少，建议增加相关内容',
    type: 'success',
    priority: 'success',
    priorityText: '低',
    icon: 'SuccessFilled'
  }
])

// 最近活动
const recentActivities = reactive([
  {
    id: 1,
    title: '新增知识条目',
    description: '用户张三添加了《Vue3组件开发指南》',
    time: '2小时前',
    type: 'add',
    icon: 'Plus'
  },
  {
    id: 2,
    title: '内容更新',
    description: '《React Hooks最佳实践》已更新',
    time: '4小时前',
    type: 'edit',
    icon: 'Edit'
  },
  {
    id: 3,
    title: '内容删除',
    description: '过期文档《jQuery使用指南》已删除',
    time: '1天前',
    type: 'delete',
    icon: 'Delete'
  }
])

// 获取评分样式类
const getScoreClass = (score: number) => {
  if (score >= 90) return 'excellent'
  if (score >= 80) return 'good'
  if (score >= 70) return 'average'
  return 'poor'
}

// 获取进度条颜色
const getProgressColor = (score: number) => {
  if (score >= 90) return '#67c23a'
  if (score >= 80) return '#409eff'
  if (score >= 70) return '#e6a23c'
  return '#f56c6c'
}

// 初始化分布图表
const initDistributionChart = () => {
  if (!distributionChart.value) return
  
  distributionChartInstance = echarts.init(distributionChart.value)
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '知识分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '18',
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: 1048, name: '技术文档' },
          { value: 735, name: '产品说明' },
          { value: 580, name: '流程规范' },
          { value: 484, name: '培训资料' },
          { value: 300, name: '其他' }
        ]
      }
    ]
  }
  
  distributionChartInstance.setOption(option)
}

// 初始化趋势图表
const initTrendChart = () => {
  if (!trendChart.value) return
  
  trendChartInstance = echarts.init(trendChart.value)
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['新增', '更新', '删除']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '新增',
        type: 'line',
        stack: 'Total',
        data: [120, 132, 101, 134, 90, 230, 210]
      },
      {
        name: '更新',
        type: 'line',
        stack: 'Total',
        data: [220, 182, 191, 234, 290, 330, 310]
      },
      {
        name: '删除',
        type: 'line',
        stack: 'Total',
        data: [150, 232, 201, 154, 190, 330, 410]
      }
    ]
  }
  
  trendChartInstance.setOption(option)
}

// 初始化热门内容图表
const initHotContentChart = () => {
  if (!hotContentChart.value) return
  
  hotContentChartInstance = echarts.init(hotContentChart.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      boundaryGap: [0, 0.01]
    },
    yAxis: {
      type: 'category',
      data: ['Vue3指南', 'React教程', 'Node.js实战', 'TypeScript入门', 'Webpack配置']
    },
    series: [
      {
        name: '访问量',
        type: 'bar',
        data: [18203, 23489, 29034, 104970, 131744]
      }
    ]
  }
  
  hotContentChartInstance.setOption(option)
}

// 刷新分析
const refreshAnalysis = async () => {
  try {
    ElMessage.success('分析数据已刷新')
    // 这里可以调用API刷新数据
  } catch (error) {
    ElMessage.error('刷新失败，请稍后重试')
  }
}

// 导出报告
const exportReport = async () => {
  try {
    ElMessage.success('报告导出成功')
    // 这里可以调用API导出报告
  } catch (error) {
    ElMessage.error('导出失败，请稍后重试')
  }
}

// 应用建议
const applySuggestion = async (suggestion: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要应用建议「${suggestion.title}」吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('建议已应用')
    // 这里可以调用API应用建议
  } catch {
    // 用户取消
  }
}

// 忽略建议
const ignoreSuggestion = (suggestion: any) => {
  const index = suggestions.findIndex(s => s.id === suggestion.id)
  if (index > -1) {
    suggestions.splice(index, 1)
    ElMessage.info('建议已忽略')
  }
}

// 窗口大小变化处理
const handleResize = () => {
  distributionChartInstance?.resize()
  trendChartInstance?.resize()
  hotContentChartInstance?.resize()
}

onMounted(async () => {
  await nextTick()
  initDistributionChart()
  initTrendChart()
  initHotContentChart()
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  distributionChartInstance?.dispose()
  trendChartInstance?.dispose()
  hotContentChartInstance?.dispose()
  
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.knowledge-analysis {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.analysis-header {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-info {
      .page-title {
        font-size: 28px;
        font-weight: 600;
        color: #303133;
        margin: 0 0 8px 0;
        display: flex;
        align-items: center;
        gap: 12px;
        
        .el-icon {
          color: #409eff;
        }
      }
      
      .page-description {
        color: #606266;
        margin: 0;
        font-size: 14px;
      }
    }
    
    .header-actions {
      display: flex;
      gap: 12px;
    }
  }
}

.stats-cards {
  margin-bottom: 20px;
  
  .stat-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    }
    
    .stat-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
    }
    
    .stat-content {
      flex: 1;
      
      .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 4px;
      }
      
      .stat-label {
        color: #606266;
        font-size: 14px;
        margin-bottom: 4px;
      }
      
      .stat-change {
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 4px;
        
        &.up {
          color: #67c23a;
        }
        
        &.down {
          color: #f56c6c;
        }
      }
    }
  }
}

.analysis-content {
  .chart-card,
  .info-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .card-title {
        font-weight: 600;
        color: #303133;
        display: flex;
        align-items: center;
        gap: 8px;
        
        .el-icon {
          color: #409eff;
        }
      }
    }
    
    .chart-container {
      .chart {
        width: 100%;
        height: 300px;
      }
    }
  }
}

.quality-assessment {
  .quality-item {
    margin-bottom: 20px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .quality-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      .quality-name {
        font-weight: 500;
        color: #303133;
      }
      
      .quality-score {
        font-weight: 600;
        
        &.excellent {
          color: #67c23a;
        }
        
        &.good {
          color: #409eff;
        }
        
        &.average {
          color: #e6a23c;
        }
        
        &.poor {
          color: #f56c6c;
        }
      }
    }
    
    .quality-description {
      font-size: 12px;
      color: #909399;
      margin-top: 8px;
    }
  }
}

.suggestions {
  .suggestion-item {
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .suggestion-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      
      .suggestion-icon {
        &.info {
          color: #409eff;
        }
        
        &.warning {
          color: #e6a23c;
        }
        
        &.success {
          color: #67c23a;
        }
      }
      
      .suggestion-title {
        flex: 1;
        font-weight: 500;
        color: #303133;
      }
    }
    
    .suggestion-content {
      color: #606266;
      font-size: 14px;
      line-height: 1.5;
      margin-bottom: 12px;
    }
    
    .suggestion-actions {
      display: flex;
      gap: 8px;
    }
  }
}

.recent-activities {
  .activity-item {
    display: flex;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #f0f2f5;
    
    &:last-child {
      border-bottom: none;
    }
    
    .activity-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      
      .el-icon {
        &.add {
          color: #67c23a;
          background: rgba(103, 194, 58, 0.1);
        }
        
        &.edit {
          color: #409eff;
          background: rgba(64, 158, 255, 0.1);
        }
        
        &.delete {
          color: #f56c6c;
          background: rgba(245, 108, 108, 0.1);
        }
      }
    }
    
    .activity-content {
      flex: 1;
      
      .activity-title {
        font-weight: 500;
        color: #303133;
        margin-bottom: 4px;
      }
      
      .activity-description {
        color: #606266;
        font-size: 14px;
        margin-bottom: 4px;
      }
      
      .activity-time {
        color: #909399;
        font-size: 12px;
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .knowledge-analysis {
    padding: 10px;
  }
  
  .analysis-header {
    padding: 16px;
    
    .header-content {
      flex-direction: column;
      gap: 16px;
      align-items: flex-start;
      
      .header-actions {
        width: 100%;
        justify-content: flex-end;
      }
    }
  }
  
  .stats-cards {
    .stat-card {
      padding: 16px;
      
      .stat-icon {
        width: 48px;
        height: 48px;
      }
      
      .stat-content {
        .stat-value {
          font-size: 20px;
        }
      }
    }
  }
  
  .chart-container {
    .chart {
      height: 250px !important;
    }
  }
}
</style>