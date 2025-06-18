<template>
  <div class="etl-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Operation /></el-icon>
            ETL作业监控
          </h1>
          <p class="page-description">
            监控和管理数据抽取、转换和加载作业的执行状态
          </p>
        </div>
        <div class="header-right">
          <el-button type="primary" @click="showCreateJobDialog">
            <el-icon><Plus /></el-icon>
            创建作业
          </el-button>
          <el-button @click="showScheduleDialog">
            <el-icon><Timer /></el-icon>
            调度管理
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon running">
                <el-icon><VideoPlay /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.running }}</div>
                <div class="stat-label">运行中</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon success">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.success }}</div>
                <div class="stat-label">成功</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon failed">
                <el-icon><CircleClose /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.failed }}</div>
                <div class="stat-label">失败</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon total">
                <el-icon><DataBoard /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.total }}</div>
                <div class="stat-label">总计</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 搜索和筛选 -->
    <div class="search-section">
      <el-card shadow="never">
        <div class="search-form">
          <div class="search-row">
            <div class="search-item">
              <el-input
                v-model="searchForm.keyword"
                placeholder="搜索作业名称或描述"
                clearable
                @keyup.enter="handleSearch"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            
            <div class="search-item">
              <el-select
                v-model="searchForm.type"
                placeholder="作业类型"
                clearable
                filterable
              >
                <el-option
                  v-for="type in jobTypes"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
            </div>
            
            <div class="search-item">
              <el-select
                v-model="searchForm.status"
                placeholder="执行状态"
                clearable
              >
                <el-option label="全部" value="" />
                <el-option label="等待中" value="pending" />
                <el-option label="运行中" value="running" />
                <el-option label="已完成" value="completed" />
                <el-option label="失败" value="failed" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
            </div>
            
            <div class="search-item">
              <el-date-picker
                v-model="searchForm.dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </div>
          </div>
          
          <div class="search-actions">
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="handleReset">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
            <el-button @click="handleRefresh">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 作业列表 -->
    <div class="jobs-content">
      <el-card shadow="never">
        <el-table
          v-loading="loading"
          :data="jobsList"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="name" label="作业名称" min-width="200">
            <template #default="{ row }">
              <div class="job-name">
                <el-icon class="job-icon" :style="{ color: getJobTypeColor(row.type) }">
                  <component :is="getJobTypeIcon(row.type)" />
                </el-icon>
                <div class="name-info">
                  <div class="name">{{ row.name }}</div>
                  <div class="description">{{ row.description }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="getJobTypeTagType(row.type)">
                {{ getJobTypeLabel(row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="getStatusTagType(row.status)"
                :icon="getStatusIcon(row.status)"
              >
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="progress" label="进度" width="150">
            <template #default="{ row }">
              <div class="progress-info">
                <el-progress
                  v-if="row.status === 'running'"
                  :percentage="row.progress || 0"
                  :stroke-width="6"
                  :show-text="false"
                />
                <span class="progress-text">
                  {{ row.status === 'running' ? `${row.progress || 0}%` : '-' }}
                </span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="duration" label="执行时长" width="120">
            <template #default="{ row }">
              {{ formatDuration(row.duration) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="processedRecords" label="处理记录" width="120">
            <template #default="{ row }">
              <span class="record-count">
                {{ formatNumber(row.processedRecords) }}
              </span>
            </template>
          </el-table-column>
          
          <el-table-column prop="startTime" label="开始时间" width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.startTime) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="endTime" label="结束时间" width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.endTime) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button-group>
                <el-button size="small" @click="viewJobDetail(row)">
                  <el-icon><View /></el-icon>
                </el-button>
                <el-button size="small" @click="viewJobLogs(row)">
                  <el-icon><Document /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  :disabled="row.status === 'running'"
                  @click="restartJob(row)"
                >
                  <el-icon><Refresh /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  :disabled="row.status !== 'running'"
                  @click="stopJob(row)"
                >
                  <el-icon><VideoPause /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  @click="deleteJob(row)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.size"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>
    
    <!-- 创建作业对话框 -->
    <el-dialog
      v-model="createJobDialogVisible"
      title="创建ETL作业"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="jobFormRef"
        :model="jobForm"
        :rules="jobFormRules"
        label-width="120px"
      >
        <el-form-item label="作业名称" prop="name">
          <el-input v-model="jobForm.name" placeholder="请输入作业名称" />
        </el-form-item>
        
        <el-form-item label="作业描述" prop="description">
          <el-input
            v-model="jobForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入作业描述"
          />
        </el-form-item>
        
        <el-form-item label="作业类型" prop="type">
          <el-select v-model="jobForm.type" placeholder="请选择作业类型" style="width: 100%">
            <el-option
              v-for="type in jobTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="数据源" prop="sourceConfig">
          <el-input
            v-model="jobForm.sourceConfig"
            type="textarea"
            :rows="4"
            placeholder="请输入数据源配置（JSON格式）"
          />
        </el-form-item>
        
        <el-form-item label="目标配置" prop="targetConfig">
          <el-input
            v-model="jobForm.targetConfig"
            type="textarea"
            :rows="4"
            placeholder="请输入目标配置（JSON格式）"
          />
        </el-form-item>
        
        <el-form-item label="转换规则" prop="transformRules">
          <el-input
            v-model="jobForm.transformRules"
            type="textarea"
            :rows="6"
            placeholder="请输入转换规则（JSON格式）"
          />
        </el-form-item>
        
        <el-form-item label="调度配置">
          <el-checkbox v-model="jobForm.enableSchedule">启用定时调度</el-checkbox>
          <el-input
            v-if="jobForm.enableSchedule"
            v-model="jobForm.cronExpression"
            placeholder="Cron表达式，如：0 0 2 * * ?"
            style="margin-top: 8px;"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createJobDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="createJob">创建</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 作业详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="currentJob?.name"
      width="80%"
      :close-on-click-modal="false"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="基本信息" name="basic">
          <div class="job-detail">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="作业名称">
                {{ currentJob?.name }}
              </el-descriptions-item>
              <el-descriptions-item label="作业类型">
                <el-tag :type="getJobTypeTagType(currentJob?.type)">
                  {{ getJobTypeLabel(currentJob?.type) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="执行状态">
                <el-tag :type="getStatusTagType(currentJob?.status)">
                  {{ getStatusLabel(currentJob?.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="执行进度">
                {{ currentJob?.progress || 0 }}%
              </el-descriptions-item>
              <el-descriptions-item label="开始时间">
                {{ formatDateTime(currentJob?.startTime) }}
              </el-descriptions-item>
              <el-descriptions-item label="结束时间">
                {{ formatDateTime(currentJob?.endTime) }}
              </el-descriptions-item>
              <el-descriptions-item label="执行时长">
                {{ formatDuration(currentJob?.duration) }}
              </el-descriptions-item>
              <el-descriptions-item label="处理记录">
                {{ formatNumber(currentJob?.processedRecords) }}
              </el-descriptions-item>
            </el-descriptions>
            
            <div class="job-description">
              <h4>作业描述</h4>
              <p>{{ currentJob?.description }}</p>
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="配置信息" name="config">
          <div class="config-content">
            <el-collapse v-model="activeConfigPanel">
              <el-collapse-item title="数据源配置" name="source">
                <pre class="config-json">{{ formatJson(currentJob?.sourceConfig) }}</pre>
              </el-collapse-item>
              <el-collapse-item title="目标配置" name="target">
                <pre class="config-json">{{ formatJson(currentJob?.targetConfig) }}</pre>
              </el-collapse-item>
              <el-collapse-item title="转换规则" name="transform">
                <pre class="config-json">{{ formatJson(currentJob?.transformRules) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="执行日志" name="logs">
          <div class="logs-content">
            <div class="logs-toolbar">
              <el-button size="small" @click="refreshLogs">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button size="small" @click="downloadLogs">
                <el-icon><Download /></el-icon>
                下载日志
              </el-button>
              <el-select v-model="logLevel" size="small" style="width: 120px; margin-left: 12px;">
                <el-option label="全部" value="" />
                <el-option label="INFO" value="info" />
                <el-option label="WARN" value="warn" />
                <el-option label="ERROR" value="error" />
              </el-select>
            </div>
            <div class="logs-container">
              <div
                v-for="(log, index) in filteredLogs"
                :key="index"
                class="log-entry"
                :class="log.level"
              >
                <span class="log-time">{{ formatDateTime(log.timestamp) }}</span>
                <span class="log-level">{{ log.level.toUpperCase() }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="执行统计" name="stats">
          <div class="stats-content">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-card>
                  <template #header>
                    <span>处理统计</span>
                  </template>
                  <div class="stat-item">
                    <span class="stat-label">总记录数:</span>
                    <span class="stat-value">{{ formatNumber(currentJob?.totalRecords) }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">已处理:</span>
                    <span class="stat-value">{{ formatNumber(currentJob?.processedRecords) }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">成功:</span>
                    <span class="stat-value success">{{ formatNumber(currentJob?.successRecords) }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">失败:</span>
                    <span class="stat-value error">{{ formatNumber(currentJob?.failedRecords) }}</span>
                  </div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>
                    <span>性能指标</span>
                  </template>
                  <div class="stat-item">
                    <span class="stat-label">处理速度:</span>
                    <span class="stat-value">{{ currentJob?.processingRate || 0 }} 条/秒</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">内存使用:</span>
                    <span class="stat-value">{{ currentJob?.memoryUsage || 0 }} MB</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">CPU使用:</span>
                    <span class="stat-value">{{ currentJob?.cpuUsage || 0 }}%</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">错误率:</span>
                    <span class="stat-value">{{ calculateErrorRate(currentJob) }}%</span>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Operation,
  Plus,
  Timer,
  VideoPlay,
  CircleCheck,
  CircleClose,
  DataBoard,
  Search,
  Refresh,
  View,
  Document,
  VideoPause,
  Delete,
  Download,
  Upload,
  Files,
  Setting
} from '@element-plus/icons-vue'

// 响应式数据
const loading = ref(false)
const createJobDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const currentJob = ref<any>(null)
const activeTab = ref('basic')
const activeConfigPanel = ref(['source'])
const logLevel = ref('')
const jobFormRef = ref()
const refreshTimer = ref<any>(null)

// 统计数据
const stats = reactive({
  running: 3,
  success: 156,
  failed: 8,
  total: 167
})

// 搜索表单
const searchForm = reactive({
  keyword: '',
  type: '',
  status: '',
  dateRange: []
})

// 作业表单
const jobForm = reactive({
  name: '',
  description: '',
  type: '',
  sourceConfig: '',
  targetConfig: '',
  transformRules: '',
  enableSchedule: false,
  cronExpression: ''
})

// 表单验证规则
const jobFormRules = {
  name: [
    { required: true, message: '请输入作业名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择作业类型', trigger: 'change' }
  ],
  sourceConfig: [
    { required: true, message: '请输入数据源配置', trigger: 'blur' }
  ],
  targetConfig: [
    { required: true, message: '请输入目标配置', trigger: 'blur' }
  ]
}

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 作业列表
const jobsList = ref([
  {
    id: '1',
    name: '文档实体抽取作业',
    description: '从上传的文档中抽取实体信息',
    type: 'entity_extraction',
    status: 'running',
    progress: 75,
    duration: 1800000, // 30分钟
    processedRecords: 1250,
    totalRecords: 1500,
    successRecords: 1200,
    failedRecords: 50,
    startTime: '2024-01-15 14:30:00',
    endTime: null,
    processingRate: 25,
    memoryUsage: 512,
    cpuUsage: 45,
    sourceConfig: '{ "type": "document", "path": "/data/documents" }',
    targetConfig: '{ "type": "neo4j", "uri": "bolt://localhost:7687" }',
    transformRules: '{ "rules": [{ "field": "text", "action": "extract_entities" }] }'
  },
  {
    id: '2',
    name: '关系抽取作业',
    description: '从文本中抽取实体间的关系',
    type: 'relation_extraction',
    status: 'completed',
    progress: 100,
    duration: 2400000, // 40分钟
    processedRecords: 800,
    totalRecords: 800,
    successRecords: 780,
    failedRecords: 20,
    startTime: '2024-01-15 13:00:00',
    endTime: '2024-01-15 13:40:00',
    processingRate: 20,
    memoryUsage: 768,
    cpuUsage: 0,
    sourceConfig: '{ "type": "text", "source": "entities" }',
    targetConfig: '{ "type": "neo4j", "uri": "bolt://localhost:7687" }',
    transformRules: '{ "rules": [{ "field": "text", "action": "extract_relations" }] }'
  },
  {
    id: '3',
    name: '数据清洗作业',
    description: '清洗和标准化导入的数据',
    type: 'data_cleaning',
    status: 'failed',
    progress: 0,
    duration: 300000, // 5分钟
    processedRecords: 0,
    totalRecords: 1000,
    successRecords: 0,
    failedRecords: 0,
    startTime: '2024-01-15 12:00:00',
    endTime: '2024-01-15 12:05:00',
    processingRate: 0,
    memoryUsage: 0,
    cpuUsage: 0,
    sourceConfig: '{ "type": "csv", "path": "/data/raw.csv" }',
    targetConfig: '{ "type": "database", "table": "clean_data" }',
    transformRules: '{ "rules": [{ "field": "*", "action": "clean" }] }'
  }
])

// 作业类型
const jobTypes = ref([
  { label: '实体抽取', value: 'entity_extraction' },
  { label: '关系抽取', value: 'relation_extraction' },
  { label: '数据清洗', value: 'data_cleaning' },
  { label: '数据转换', value: 'data_transform' },
  { label: '数据同步', value: 'data_sync' },
  { label: '索引构建', value: 'index_building' }
])

// 日志数据
const logs = ref([
  {
    timestamp: '2024-01-15 14:30:00',
    level: 'info',
    message: '作业开始执行'
  },
  {
    timestamp: '2024-01-15 14:30:15',
    level: 'info',
    message: '开始处理文档: document_001.pdf'
  },
  {
    timestamp: '2024-01-15 14:30:30',
    level: 'warn',
    message: '文档格式可能存在问题，尝试自动修复'
  },
  {
    timestamp: '2024-01-15 14:30:45',
    level: 'info',
    message: '成功抽取实体: 企业, 知识管理, 流程'
  },
  {
    timestamp: '2024-01-15 14:31:00',
    level: 'error',
    message: '处理文档 document_002.pdf 时发生错误: 文件损坏'
  }
])

// 计算属性
const filteredLogs = computed(() => {
  if (!logLevel.value) return logs.value
  return logs.value.filter(log => log.level === logLevel.value)
})

// 方法
const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const formatDuration = (duration: number) => {
  if (!duration) return '-'
  const hours = Math.floor(duration / 3600000)
  const minutes = Math.floor((duration % 3600000) / 60000)
  const seconds = Math.floor((duration % 60000) / 1000)
  
  if (hours > 0) {
    return `${hours}时${minutes}分${seconds}秒`
  } else if (minutes > 0) {
    return `${minutes}分${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

const formatNumber = (num: number) => {
  if (num === undefined || num === null) return '0'
  return num.toLocaleString()
}

const formatJson = (jsonStr: string) => {
  if (!jsonStr) return ''
  try {
    return JSON.stringify(JSON.parse(jsonStr), null, 2)
  } catch (error) {
    return jsonStr
  }
}

const calculateErrorRate = (job: any) => {
  if (!job || !job.processedRecords) return 0
  return ((job.failedRecords || 0) / job.processedRecords * 100).toFixed(2)
}

const getJobTypeIcon = (type: string) => {
  const icons = {
    entity_extraction: Upload,
    relation_extraction: Files,
    data_cleaning: Setting,
    data_transform: Operation,
    data_sync: Refresh,
    index_building: DataBoard
  }
  return icons[type] || Operation
}

const getJobTypeColor = (type: string) => {
  const colors = {
    entity_extraction: '#409eff',
    relation_extraction: '#67c23a',
    data_cleaning: '#e6a23c',
    data_transform: '#f56c6c',
    data_sync: '#909399',
    index_building: '#9c27b0'
  }
  return colors[type] || '#409eff'
}

const getJobTypeTagType = (type: string) => {
  const types = {
    entity_extraction: 'primary',
    relation_extraction: 'success',
    data_cleaning: 'warning',
    data_transform: 'danger',
    data_sync: 'info',
    index_building: 'info'
  }
  return types[type] || 'info'
}

const getJobTypeLabel = (type: string) => {
  const typeObj = jobTypes.value.find(t => t.value === type)
  return typeObj ? typeObj.label : type
}

const getStatusTagType = (status: string) => {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const labels = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return labels[status] || status
}

const getStatusIcon = (status: string) => {
  // 这里可以返回对应的图标组件
  return null
}

// 搜索和筛选
const handleSearch = () => {
  pagination.page = 1
  loadJobs()
}

const handleReset = () => {
  Object.assign(searchForm, {
    keyword: '',
    type: '',
    status: '',
    dateRange: []
  })
  handleSearch()
}

const handleRefresh = () => {
  loadJobs()
  loadStats()
}

// 分页
const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  loadJobs()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadJobs()
}

// 作业操作
const showCreateJobDialog = () => {
  Object.assign(jobForm, {
    name: '',
    description: '',
    type: '',
    sourceConfig: '',
    targetConfig: '',
    transformRules: '',
    enableSchedule: false,
    cronExpression: ''
  })
  createJobDialogVisible.value = true
}

const showScheduleDialog = () => {
  ElMessage.info('调度管理功能开发中...')
}

const createJob = async () => {
  try {
    await jobFormRef.value?.validate()
    
    // 这里调用API创建作业
    ElMessage.success('作业创建成功')
    createJobDialogVisible.value = false
    loadJobs()
    
  } catch (error) {
    ElMessage.error('请检查表单输入')
  }
}

const viewJobDetail = (job: any) => {
  currentJob.value = job
  activeTab.value = 'basic'
  detailDialogVisible.value = true
}

const viewJobLogs = (job: any) => {
  currentJob.value = job
  activeTab.value = 'logs'
  detailDialogVisible.value = true
}

const restartJob = async (job: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要重新启动作业 "${job.name}" 吗？`,
      '重新启动',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('作业已重新启动')
    loadJobs()
    
  } catch (error) {
    // 用户取消
  }
}

const stopJob = async (job: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要停止作业 "${job.name}" 吗？`,
      '停止作业',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('作业已停止')
    loadJobs()
    
  } catch (error) {
    // 用户取消
  }
}

const deleteJob = async (job: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除作业 "${job.name}" 吗？此操作不可恢复。`,
      '删除作业',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('作业已删除')
    loadJobs()
    
  } catch (error) {
    // 用户取消
  }
}

// 日志操作
const refreshLogs = () => {
  ElMessage.info('日志已刷新')
}

const downloadLogs = () => {
  ElMessage.info('日志下载功能开发中...')
}

// 加载数据
const loadJobs = async () => {
  loading.value = true
  try {
    // 这里调用API加载作业列表
    // const response = await etlApi.getJobs(searchForm, pagination)
    // jobsList.value = response.data.items
    // pagination.total = response.data.total
    
    // 模拟加载延迟
    await new Promise(resolve => setTimeout(resolve, 500))
    
  } catch (error) {
    ElMessage.error('加载作业列表失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    // 这里调用API加载统计数据
    // const response = await etlApi.getStats()
    // Object.assign(stats, response.data)
    
  } catch (error) {
    ElMessage.error('加载统计数据失败')
  }
}

// 自动刷新
const startAutoRefresh = () => {
  refreshTimer.value = setInterval(() => {
    loadJobs()
    loadStats()
  }, 30000) // 30秒刷新一次
}

const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
}

// 生命周期
onMounted(() => {
  loadJobs()
  loadStats()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.etl-page {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-description {
  color: #6b7280;
  margin: 0;
  font-size: 14px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.stats-section {
  margin-bottom: 20px;
}

.stat-card {
  height: 100%;
}

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
  font-size: 24px;
  color: white;
}

.stat-icon.running {
  background: #f59e0b;
}

.stat-icon.success {
  background: #10b981;
}

.stat-icon.failed {
  background: #ef4444;
}

.stat-icon.total {
  background: #6366f1;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

.search-section {
  margin-bottom: 20px;
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.search-item {
  min-width: 200px;
  flex: 1;
}

.search-actions {
  display: flex;
  gap: 12px;
}

.jobs-content {
  margin-bottom: 20px;
}

.job-name {
  display: flex;
  align-items: center;
  gap: 12px;
}

.job-icon {
  font-size: 20px;
}

.name-info {
  flex: 1;
}

.name {
  font-weight: 500;
  color: #1f2937;
}

.description {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-text {
  font-size: 12px;
  color: #6b7280;
  min-width: 40px;
}

.record-count {
  font-weight: 500;
  color: #1f2937;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.job-detail {
  padding: 20px;
}

.job-description {
  margin-top: 20px;
}

.job-description h4 {
  margin: 0 0 12px 0;
  color: #1f2937;
}

.config-content {
  padding: 20px;
}

.config-json {
  background: #f3f4f6;
  padding: 16px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}

.logs-content {
  padding: 20px;
}

.logs-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.logs-container {
  background: #1f2937;
  border-radius: 4px;
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}

.log-entry {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
  color: #d1d5db;
}

.log-entry.info {
  color: #60a5fa;
}

.log-entry.warn {
  color: #fbbf24;
}

.log-entry.error {
  color: #f87171;
}

.log-time {
  color: #9ca3af;
  min-width: 140px;
}

.log-level {
  min-width: 50px;
  font-weight: 600;
}

.log-message {
  flex: 1;
}

.stats-content {
  padding: 20px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #6b7280;
  font-size: 14px;
}

.stat-value {
  font-weight: 500;
  color: #1f2937;
}

.stat-value.success {
  color: #10b981;
}

.stat-value.error {
  color: #ef4444;
}

@media (max-width: 768px) {
  .etl-page {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .search-row {
    flex-direction: column;
  }
  
  .search-item {
    min-width: auto;
  }
  
  .stats-section .el-col {
    margin-bottom: 12px;
  }
}
</style>