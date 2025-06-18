<template>
  <div class="search-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Search /></el-icon>
            智能搜索
          </h1>
          <p class="page-description">
            基于知识图谱的智能搜索和查询系统
          </p>
        </div>
        <div class="header-right">
          <el-button @click="showAdvancedSearch">
            <el-icon><Setting /></el-icon>
            高级搜索
          </el-button>
          <el-button @click="showSearchHistory">
            <el-icon><Clock /></el-icon>
            搜索历史
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 搜索区域 -->
    <div class="search-section">
      <el-card shadow="never" class="search-card">
        <div class="search-container">
          <div class="search-input-wrapper">
            <el-input
              v-model="searchQuery"
              class="search-input"
              placeholder="请输入搜索关键词，支持自然语言查询..."
              size="large"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
              <template #suffix>
                <el-button-group>
                  <el-button
                    size="small"
                    @click="handleVoiceSearch"
                    :disabled="isRecording"
                  >
                    <el-icon><Microphone /></el-icon>
                  </el-button>
                  <el-button size="small" @click="showSearchTips">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-button>
                </el-button-group>
              </template>
            </el-input>
            <el-button
              type="primary"
              size="large"
              class="search-button"
              :loading="searching"
              @click="handleSearch"
            >
              搜索
            </el-button>
          </div>
          
          <!-- 搜索建议 -->
          <div v-if="suggestions.length > 0" class="search-suggestions">
            <div class="suggestions-header">
              <span>搜索建议</span>
              <el-button text size="small" @click="clearSuggestions">
                清除
              </el-button>
            </div>
            <div class="suggestions-list">
              <el-tag
                v-for="(suggestion, index) in suggestions"
                :key="index"
                class="suggestion-tag"
                @click="applySuggestion(suggestion)"
              >
                {{ suggestion }}
              </el-tag>
            </div>
          </div>
          
          <!-- 快速搜索标签 -->
          <div class="quick-search">
            <span class="quick-search-label">热门搜索:</span>
            <el-tag
              v-for="tag in hotSearchTags"
              :key="tag"
              class="hot-tag"
              @click="applyQuickSearch(tag)"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 搜索结果 -->
    <div v-if="hasSearched" class="results-section">
      <!-- 结果统计 -->
      <div class="results-header">
        <div class="results-stats">
          <span class="results-count">
            找到 <strong>{{ totalResults }}</strong> 个结果
          </span>
          <span class="search-time">
            (用时 {{ searchTime }}ms)
          </span>
        </div>
        
        <div class="results-controls">
          <el-select v-model="sortBy" size="small" style="width: 120px;">
            <el-option label="相关性" value="relevance" />
            <el-option label="时间" value="time" />
            <el-option label="类型" value="type" />
          </el-select>
          
          <el-button-group>
            <el-button
              size="small"
              :type="viewMode === 'list' ? 'primary' : ''"
              @click="viewMode = 'list'"
            >
              <el-icon><List /></el-icon>
            </el-button>
            <el-button
              size="small"
              :type="viewMode === 'graph' ? 'primary' : ''"
              @click="viewMode = 'graph'"
            >
              <el-icon><Share /></el-icon>
            </el-button>
          </el-button-group>
        </div>
      </div>
      
      <!-- 搜索结果内容 -->
      <div class="results-content">
        <el-row :gutter="20">
          <!-- 左侧筛选 -->
          <el-col :span="6">
            <el-card shadow="never" class="filters-card">
              <template #header>
                <div class="filters-header">
                  <span>筛选条件</span>
                  <el-button text size="small" @click="clearFilters">
                    清除
                  </el-button>
                </div>
              </template>
              
              <!-- 结果类型筛选 -->
              <div class="filter-group">
                <h4 class="filter-title">结果类型</h4>
                <el-checkbox-group v-model="filters.types">
                  <el-checkbox
                    v-for="type in resultTypes"
                    :key="type.value"
                    :label="type.value"
                  >
                    {{ type.label }}
                    <span class="type-count">({{ type.count }})</span>
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              
              <!-- 知识图谱筛选 -->
              <div class="filter-group">
                <h4 class="filter-title">知识图谱</h4>
                <el-checkbox-group v-model="filters.graphs">
                  <el-checkbox
                    v-for="graph in availableGraphs"
                    :key="graph.id"
                    :label="graph.id"
                  >
                    {{ graph.name }}
                    <span class="type-count">({{ graph.resultCount }})</span>
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              
              <!-- 时间范围筛选 -->
              <div class="filter-group">
                <h4 class="filter-title">时间范围</h4>
                <el-radio-group v-model="filters.timeRange" direction="vertical">
                  <el-radio label="all">全部时间</el-radio>
                  <el-radio label="today">今天</el-radio>
                  <el-radio label="week">最近一周</el-radio>
                  <el-radio label="month">最近一月</el-radio>
                  <el-radio label="year">最近一年</el-radio>
                  <el-radio label="custom">自定义</el-radio>
                </el-radio-group>
                
                <el-date-picker
                  v-if="filters.timeRange === 'custom'"
                  v-model="filters.customDateRange"
                  type="daterange"
                  size="small"
                  style="width: 100%; margin-top: 8px;"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                />
              </div>
              
              <!-- 相关性筛选 -->
              <div class="filter-group">
                <h4 class="filter-title">相关性阈值</h4>
                <el-slider
                  v-model="filters.relevanceThreshold"
                  :min="0"
                  :max="100"
                  :step="5"
                  show-stops
                  show-tooltip
                />
                <div class="threshold-labels">
                  <span>低</span>
                  <span>高</span>
                </div>
              </div>
            </el-card>
          </el-col>
          
          <!-- 右侧结果 -->
          <el-col :span="18">
            <!-- 列表视图 -->
            <div v-if="viewMode === 'list'" class="results-list">
              <el-card
                v-for="result in searchResults"
                :key="result.id"
                class="result-item"
                shadow="hover"
              >
                <div class="result-header">
                  <div class="result-type">
                    <el-icon :style="{ color: getResultTypeColor(result.type) }">
                      <component :is="getResultTypeIcon(result.type)" />
                    </el-icon>
                    <el-tag size="small" :type="getResultTypeTagType(result.type)">
                      {{ getResultTypeLabel(result.type) }}
                    </el-tag>
                  </div>
                  
                  <div class="result-score">
                    <el-rate
                      v-model="result.relevanceScore"
                      :max="5"
                      disabled
                      show-score
                      text-color="#ff9900"
                      score-template="{value}分"
                    />
                  </div>
                </div>
                
                <div class="result-content">
                  <h3 class="result-title" @click="viewResultDetail(result)">
                    <span v-html="highlightKeywords(result.title)"></span>
                  </h3>
                  
                  <p class="result-description">
                    <span v-html="highlightKeywords(result.description)"></span>
                  </p>
                  
                  <div class="result-meta">
                    <span class="meta-item">
                      <el-icon><Calendar /></el-icon>
                      {{ formatDate(result.createdAt) }}
                    </span>
                    <span class="meta-item">
                      <el-icon><Collection /></el-icon>
                      {{ result.graphName }}
                    </span>
                    <span v-if="result.entityCount" class="meta-item">
                      <el-icon><User /></el-icon>
                      {{ result.entityCount }} 个实体
                    </span>
                    <span v-if="result.relationCount" class="meta-item">
                      <el-icon><Connection /></el-icon>
                      {{ result.relationCount }} 个关系
                    </span>
                  </div>
                  
                  <!-- 相关实体 -->
                  <div v-if="result.relatedEntities?.length" class="related-entities">
                    <span class="related-label">相关实体:</span>
                    <el-tag
                      v-for="entity in result.relatedEntities.slice(0, 5)"
                      :key="entity.id"
                      size="small"
                      class="entity-tag"
                      @click="searchEntity(entity)"
                    >
                      {{ entity.name }}
                    </el-tag>
                    <span v-if="result.relatedEntities.length > 5" class="more-entities">
                      +{{ result.relatedEntities.length - 5 }} 更多
                    </span>
                  </div>
                </div>
                
                <div class="result-actions">
                  <el-button size="small" @click="viewResultDetail(result)">
                    <el-icon><View /></el-icon>
                    查看详情
                  </el-button>
                  <el-button size="small" @click="exploreRelations(result)">
                    <el-icon><Share /></el-icon>
                    探索关系
                  </el-button>
                  <el-button size="small" @click="addToCollection(result)">
                    <el-icon><Star /></el-icon>
                    收藏
                  </el-button>
                  <el-button size="small" @click="exportResult(result)">
                    <el-icon><Download /></el-icon>
                    导出
                  </el-button>
                </div>
              </el-card>
              
              <!-- 分页 -->
              <div class="pagination-wrapper">
                <el-pagination
                  v-model:current-page="pagination.page"
                  v-model:page-size="pagination.size"
                  :page-sizes="[10, 20, 50]"
                  :total="totalResults"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="handleSizeChange"
                  @current-change="handleCurrentChange"
                />
              </div>
            </div>
            
            <!-- 图谱视图 -->
            <div v-else-if="viewMode === 'graph'" class="graph-view">
              <el-card shadow="never" class="graph-card">
                <template #header>
                  <div class="graph-header">
                    <span>关系图谱</span>
                    <div class="graph-controls">
                      <el-button size="small" @click="resetGraphView">
                        <el-icon><Refresh /></el-icon>
                        重置视图
                      </el-button>
                      <el-button size="small" @click="exportGraph">
                        <el-icon><Download /></el-icon>
                        导出图谱
                      </el-button>
                    </div>
                  </div>
                </template>
                
                <div class="graph-container" ref="graphContainer">
                  <!-- 这里将集成图谱可视化组件 -->
                  <div class="graph-placeholder">
                    <el-icon class="graph-icon"><Share /></el-icon>
                    <p>图谱可视化组件</p>
                    <p class="graph-description">
                      显示搜索结果中实体和关系的图谱结构
                    </p>
                  </div>
                </div>
              </el-card>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
    
    <!-- 高级搜索对话框 -->
    <el-dialog
      v-model="advancedSearchVisible"
      title="高级搜索"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-form :model="advancedForm" label-width="120px">
        <el-form-item label="搜索模式">
          <el-radio-group v-model="advancedForm.searchMode">
            <el-radio label="semantic">语义搜索</el-radio>
            <el-radio label="keyword">关键词搜索</el-radio>
            <el-radio label="fuzzy">模糊搜索</el-radio>
            <el-radio label="exact">精确匹配</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="搜索范围">
          <el-checkbox-group v-model="advancedForm.searchScope">
            <el-checkbox label="entities">实体</el-checkbox>
            <el-checkbox label="relations">关系</el-checkbox>
            <el-checkbox label="documents">文档</el-checkbox>
            <el-checkbox label="properties">属性</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <el-form-item label="实体类型">
          <el-select
            v-model="advancedForm.entityTypes"
            multiple
            placeholder="选择实体类型"
            style="width: 100%"
          >
            <el-option
              v-for="type in entityTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="关系类型">
          <el-select
            v-model="advancedForm.relationTypes"
            multiple
            placeholder="选择关系类型"
            style="width: 100%"
          >
            <el-option
              v-for="type in relationTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="路径长度">
          <el-slider
            v-model="advancedForm.pathLength"
            :min="1"
            :max="5"
            :step="1"
            show-stops
            show-tooltip
          />
        </el-form-item>
        
        <el-form-item label="结果限制">
          <el-input-number
            v-model="advancedForm.resultLimit"
            :min="10"
            :max="1000"
            :step="10"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="advancedSearchVisible = false">取消</el-button>
          <el-button type="primary" @click="applyAdvancedSearch">应用</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 搜索历史对话框 -->
    <el-dialog
      v-model="historyDialogVisible"
      title="搜索历史"
      width="600px"
    >
      <div class="search-history">
        <div
          v-for="(item, index) in searchHistory"
          :key="index"
          class="history-item"
          @click="applyHistorySearch(item)"
        >
          <div class="history-content">
            <div class="history-query">{{ item.query }}</div>
            <div class="history-meta">
              <span class="history-time">{{ formatDate(item.timestamp) }}</span>
              <span class="history-results">{{ item.resultCount }} 个结果</span>
            </div>
          </div>
          <el-button
            size="small"
            text
            @click.stop="removeHistoryItem(index)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="clearSearchHistory">清空历史</el-button>
          <el-button type="primary" @click="historyDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Setting,
  Clock,
  Microphone,
  QuestionFilled,
  List,
  Share,
  Calendar,
  Collection,
  User,
  Connection,
  View,
  Star,
  Download,
  Refresh,
  Delete,
  Document,
  Files,
  Picture,
  VideoPlay
} from '@element-plus/icons-vue'

// 响应式数据
const searchQuery = ref('')
const searching = ref(false)
const hasSearched = ref(false)
const viewMode = ref('list')
const sortBy = ref('relevance')
const totalResults = ref(0)
const searchTime = ref(0)
const isRecording = ref(false)
const advancedSearchVisible = ref(false)
const historyDialogVisible = ref(false)
const graphContainer = ref()

// 搜索建议
const suggestions = ref([
  '知识管理系统',
  '人工智能技术',
  '数据挖掘算法',
  '机器学习模型'
])

// 热门搜索标签
const hotSearchTags = ref([
  '人工智能',
  '机器学习',
  '知识图谱',
  '自然语言处理',
  '深度学习',
  '数据科学'
])

// 筛选条件
const filters = reactive({
  types: ['entity', 'relation', 'document'],
  graphs: [],
  timeRange: 'all',
  customDateRange: [],
  relevanceThreshold: 60
})

// 高级搜索表单
const advancedForm = reactive({
  searchMode: 'semantic',
  searchScope: ['entities', 'relations'],
  entityTypes: [],
  relationTypes: [],
  pathLength: 2,
  resultLimit: 100
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20
})

// 结果类型
const resultTypes = ref([
  { label: '实体', value: 'entity', count: 45 },
  { label: '关系', value: 'relation', count: 23 },
  { label: '文档', value: 'document', count: 12 },
  { label: '图谱', value: 'graph', count: 3 }
])

// 可用知识图谱
const availableGraphs = ref([
  { id: '1', name: '企业知识图谱', resultCount: 35 },
  { id: '2', name: '技术知识图谱', resultCount: 28 },
  { id: '3', name: '产品知识图谱', resultCount: 20 }
])

// 实体类型
const entityTypes = ref([
  { label: '人员', value: 'person' },
  { label: '组织', value: 'organization' },
  { label: '概念', value: 'concept' },
  { label: '技术', value: 'technology' },
  { label: '产品', value: 'product' }
])

// 关系类型
const relationTypes = ref([
  { label: '属于', value: 'belongs_to' },
  { label: '包含', value: 'contains' },
  { label: '相关', value: 'related_to' },
  { label: '依赖', value: 'depends_on' },
  { label: '实现', value: 'implements' }
])

// 搜索结果
const searchResults = ref([
  {
    id: '1',
    type: 'entity',
    title: '人工智能技术',
    description: '人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。',
    relevanceScore: 4.5,
    createdAt: '2024-01-15',
    graphName: '技术知识图谱',
    entityCount: 15,
    relationCount: 8,
    relatedEntities: [
      { id: 'e1', name: '机器学习' },
      { id: 'e2', name: '深度学习' },
      { id: 'e3', name: '神经网络' },
      { id: 'e4', name: '自然语言处理' },
      { id: 'e5', name: '计算机视觉' },
      { id: 'e6', name: '专家系统' }
    ]
  },
  {
    id: '2',
    type: 'relation',
    title: '机器学习 → 实现 → 人工智能',
    description: '机器学习是实现人工智能的重要技术手段，通过算法让计算机从数据中学习模式。',
    relevanceScore: 4.2,
    createdAt: '2024-01-14',
    graphName: '技术知识图谱',
    relatedEntities: [
      { id: 'e1', name: '算法' },
      { id: 'e2', name: '数据挖掘' },
      { id: 'e3', name: '模式识别' }
    ]
  },
  {
    id: '3',
    type: 'document',
    title: '人工智能发展报告2024',
    description: '详细分析了人工智能技术在各个领域的应用现状和发展趋势，包括技术突破、产业应用等。',
    relevanceScore: 4.0,
    createdAt: '2024-01-10',
    graphName: '企业知识图谱',
    entityCount: 25,
    relationCount: 12,
    relatedEntities: [
      { id: 'e1', name: '技术趋势' },
      { id: 'e2', name: '产业应用' },
      { id: 'e3', name: '市场分析' }
    ]
  }
])

// 搜索历史
const searchHistory = ref([
  {
    query: '人工智能技术发展',
    timestamp: '2024-01-15 14:30:00',
    resultCount: 156
  },
  {
    query: '机器学习算法',
    timestamp: '2024-01-15 10:15:00',
    resultCount: 89
  },
  {
    query: '知识图谱构建',
    timestamp: '2024-01-14 16:45:00',
    resultCount: 67
  }
])

// 计算属性
const filteredResults = computed(() => {
  // 这里可以根据筛选条件过滤结果
  return searchResults.value
})

// 方法
const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getResultTypeIcon = (type: string) => {
  const icons = {
    entity: User,
    relation: Connection,
    document: Document,
    graph: Share,
    image: Picture,
    video: VideoPlay
  }
  return icons[type] || Document
}

const getResultTypeColor = (type: string) => {
  const colors = {
    entity: '#409eff',
    relation: '#67c23a',
    document: '#e6a23c',
    graph: '#f56c6c',
    image: '#9c27b0',
    video: '#ff5722'
  }
  return colors[type] || '#409eff'
}

const getResultTypeTagType = (type: string) => {
  const types = {
    entity: 'primary',
    relation: 'success',
    document: 'warning',
    graph: 'danger',
    image: 'info',
    video: 'info'
  }
  return types[type] || 'info'
}

const getResultTypeLabel = (type: string) => {
  const labels = {
    entity: '实体',
    relation: '关系',
    document: '文档',
    graph: '图谱',
    image: '图片',
    video: '视频'
  }
  return labels[type] || type
}

const highlightKeywords = (text: string) => {
  if (!searchQuery.value || !text) return text
  const keywords = searchQuery.value.split(' ').filter(k => k.trim())
  let highlightedText = text
  
  keywords.forEach(keyword => {
    const regex = new RegExp(`(${keyword})`, 'gi')
    highlightedText = highlightedText.replace(regex, '<mark>$1</mark>')
  })
  
  return highlightedText
}

// 搜索相关方法
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  searching.value = true
  const startTime = Date.now()
  
  try {
    // 这里调用搜索API
    // const response = await searchApi.search({
    //   query: searchQuery.value,
    //   filters: filters,
    //   pagination: pagination
    // })
    // searchResults.value = response.data.results
    // totalResults.value = response.data.total
    
    // 模拟搜索延迟
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    searchTime.value = Date.now() - startTime
    totalResults.value = searchResults.value.length
    hasSearched.value = true
    
    // 添加到搜索历史
    addToSearchHistory(searchQuery.value, totalResults.value)
    
    ElMessage.success('搜索完成')
    
  } catch (error) {
    ElMessage.error('搜索失败，请重试')
  } finally {
    searching.value = false
  }
}

const handleVoiceSearch = () => {
  ElMessage.info('语音搜索功能开发中...')
}

const showSearchTips = () => {
  ElMessageBox.alert(
    '搜索技巧：\n' +
    '1. 支持自然语言查询，如"找到与人工智能相关的技术"\n' +
    '2. 使用引号进行精确匹配，如"机器学习"\n' +
    '3. 使用AND、OR进行逻辑组合\n' +
    '4. 支持通配符*进行模糊匹配',
    '搜索帮助',
    {
      confirmButtonText: '知道了'
    }
  )
}

const applySuggestion = (suggestion: string) => {
  searchQuery.value = suggestion
  handleSearch()
}

const clearSuggestions = () => {
  suggestions.value = []
}

const applyQuickSearch = (tag: string) => {
  searchQuery.value = tag
  handleSearch()
}

// 筛选相关方法
const clearFilters = () => {
  Object.assign(filters, {
    types: ['entity', 'relation', 'document'],
    graphs: [],
    timeRange: 'all',
    customDateRange: [],
    relevanceThreshold: 60
  })
  if (hasSearched.value) {
    handleSearch()
  }
}

// 分页方法
const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  handleSearch()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  handleSearch()
}

// 结果操作方法
const viewResultDetail = (result: any) => {
  ElMessage.info(`查看详情: ${result.title}`)
}

const exploreRelations = (result: any) => {
  ElMessage.info(`探索关系: ${result.title}`)
}

const addToCollection = (result: any) => {
  ElMessage.success(`已收藏: ${result.title}`)
}

const exportResult = (result: any) => {
  ElMessage.info(`导出: ${result.title}`)
}

const searchEntity = (entity: any) => {
  searchQuery.value = entity.name
  handleSearch()
}

// 图谱视图方法
const resetGraphView = () => {
  ElMessage.info('重置图谱视图')
}

const exportGraph = () => {
  ElMessage.info('导出图谱功能开发中...')
}

// 高级搜索方法
const showAdvancedSearch = () => {
  advancedSearchVisible.value = true
}

const applyAdvancedSearch = () => {
  advancedSearchVisible.value = false
  handleSearch()
}

// 搜索历史方法
const showSearchHistory = () => {
  historyDialogVisible.value = true
}

const addToSearchHistory = (query: string, resultCount: number) => {
  const historyItem = {
    query,
    timestamp: new Date().toLocaleString('zh-CN'),
    resultCount
  }
  
  // 避免重复
  const existingIndex = searchHistory.value.findIndex(item => item.query === query)
  if (existingIndex > -1) {
    searchHistory.value.splice(existingIndex, 1)
  }
  
  searchHistory.value.unshift(historyItem)
  
  // 限制历史记录数量
  if (searchHistory.value.length > 20) {
    searchHistory.value = searchHistory.value.slice(0, 20)
  }
}

const applyHistorySearch = (item: any) => {
  searchQuery.value = item.query
  historyDialogVisible.value = false
  handleSearch()
}

const removeHistoryItem = (index: number) => {
  searchHistory.value.splice(index, 1)
}

const clearSearchHistory = () => {
  searchHistory.value = []
  ElMessage.success('搜索历史已清空')
}

// 生命周期
onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.search-page {
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

.search-section {
  margin-bottom: 30px;
}

.search-card {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.search-container {
  padding: 20px;
}

.search-input-wrapper {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
}

.search-button {
  height: 40px;
  padding: 0 24px;
}

.search-suggestions {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.suggestions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.suggestions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-tag {
  cursor: pointer;
  transition: all 0.3s ease;
}

.suggestion-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.quick-search {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.quick-search-label {
  font-size: 14px;
  color: #6b7280;
  white-space: nowrap;
}

.hot-tag {
  cursor: pointer;
  transition: all 0.3s ease;
}

.hot-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.results-section {
  margin-bottom: 20px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 16px 24px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.results-stats {
  display: flex;
  align-items: center;
  gap: 12px;
}

.results-count {
  font-size: 16px;
  color: #1f2937;
}

.search-time {
  font-size: 14px;
  color: #6b7280;
}

.results-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.results-content {
  margin-bottom: 20px;
}

.filters-card {
  position: sticky;
  top: 20px;
}

.filters-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-group {
  margin-bottom: 24px;
}

.filter-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 12px 0;
}

.type-count {
  font-size: 12px;
  color: #6b7280;
  margin-left: 4px;
}

.threshold-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  transition: all 0.3s ease;
}

.result-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.result-type {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-score {
  display: flex;
  align-items: center;
}

.result-content {
  margin-bottom: 16px;
}

.result-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
  cursor: pointer;
  transition: color 0.3s ease;
}

.result-title:hover {
  color: #3b82f6;
}

.result-description {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 12px 0;
}

.result-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.related-entities {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.related-label {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.entity-tag {
  cursor: pointer;
  transition: all 0.3s ease;
}

.entity-tag:hover {
  transform: translateY(-1px);
}

.more-entities {
  font-size: 12px;
  color: #6b7280;
}

.result-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.graph-view {
  margin-bottom: 20px;
}

.graph-card {
  min-height: 600px;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.graph-controls {
  display: flex;
  gap: 8px;
}

.graph-container {
  height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border-radius: 8px;
}

.graph-placeholder {
  text-align: center;
  color: #6b7280;
}

.graph-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.graph-description {
  font-size: 14px;
  margin: 8px 0 0 0;
}

.search-history {
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.history-item:hover {
  background-color: #f3f4f6;
}

.history-content {
  flex: 1;
}

.history-query {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 4px;
}

.history-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #6b7280;
}

.history-time,
.history-results {
  white-space: nowrap;
}

/* 高亮样式 */
:deep(mark) {
  background-color: #fef3c7;
  color: #92400e;
  padding: 1px 2px;
  border-radius: 2px;
}

@media (max-width: 768px) {
  .search-page {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .search-input-wrapper {
    flex-direction: column;
  }
  
  .search-button {
    width: 100%;
  }
  
  .quick-search {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .results-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .results-content .el-col {
    margin-bottom: 20px;
  }
  
  .result-meta {
    flex-direction: column;
    gap: 8px;
  }
  
  .result-actions {
    justify-content: center;
  }
}
</style>