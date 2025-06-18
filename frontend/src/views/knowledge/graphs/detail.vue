<template>
  <div class="graph-detail">
    <!-- 页面头部 -->
    <div class="detail-header">
      <div class="header-content">
        <div class="breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/knowledge' }">知识库</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ path: '/knowledge/graphs' }">知识图谱</el-breadcrumb-item>
            <el-breadcrumb-item>{{ graphData.name || '图谱详情' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-actions">
          <el-button @click="$router.go(-1)">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <el-button @click="exportGraph">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
          <el-button type="primary" @click="editGraph">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
      </div>
    </div>

    <!-- 图谱信息卡片 -->
    <div class="graph-info-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>图谱信息</h3>
            <div class="graph-status">
              <el-tag :type="getStatusType(graphData.status)">{{ graphData.status }}</el-tag>
            </div>
          </div>
        </template>
        
        <div class="graph-info">
          <div class="info-grid">
            <div class="info-item">
              <span class="label">图谱名称：</span>
              <span class="value">{{ graphData.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">图谱类型：</span>
              <span class="value">{{ graphData.type }}</span>
            </div>
            <div class="info-item">
              <span class="label">创建时间：</span>
              <span class="value">{{ formatDate(graphData.createTime) }}</span>
            </div>
            <div class="info-item">
              <span class="label">更新时间：</span>
              <span class="value">{{ formatDate(graphData.updateTime) }}</span>
            </div>
            <div class="info-item">
              <span class="label">创建者：</span>
              <span class="value">{{ graphData.creator }}</span>
            </div>
            <div class="info-item">
              <span class="label">节点数量：</span>
              <span class="value">{{ graphData.nodeCount }} 个</span>
            </div>
            <div class="info-item">
              <span class="label">关系数量：</span>
              <span class="value">{{ graphData.edgeCount }} 个</span>
            </div>
            <div class="info-item">
              <span class="label">访问权限：</span>
              <span class="value">{{ graphData.permission }}</span>
            </div>
          </div>
          
          <div class="graph-description" v-if="graphData.description">
            <h4>描述</h4>
            <p>{{ graphData.description }}</p>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 图谱可视化 -->
    <div class="graph-visualization-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>图谱可视化</h3>
            <div class="visualization-controls">
              <el-button-group>
                <el-button size="small" @click="zoomIn">
                  <el-icon><ZoomIn /></el-icon>
                </el-button>
                <el-button size="small" @click="zoomOut">
                  <el-icon><ZoomOut /></el-icon>
                </el-button>
                <el-button size="small" @click="resetZoom">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </el-button-group>
              
              <el-select v-model="layoutType" size="small" style="width: 120px; margin-left: 12px;" @change="changeLayout">
                <el-option label="力导向" value="force" />
                <el-option label="层次" value="hierarchical" />
                <el-option label="圆形" value="circular" />
                <el-option label="网格" value="grid" />
              </el-select>
              
              <el-button size="small" @click="toggleFullscreen" style="margin-left: 12px;">
                <el-icon><FullScreen /></el-icon>
                全屏
              </el-button>
            </div>
          </div>
        </template>
        
        <div class="graph-container" ref="graphContainer" v-loading="graphLoading">
          <!-- 这里应该集成图谱可视化组件，如 D3.js、ECharts 或 Cytoscape.js -->
          <div class="graph-canvas" :class="{ 'fullscreen': isFullscreen }">
            <div class="graph-placeholder">
              <el-icon class="graph-icon"><Share /></el-icon>
              <p>知识图谱可视化</p>
              <p class="graph-stats">节点: {{ graphData.nodeCount }} | 关系: {{ graphData.edgeCount }}</p>
            </div>
          </div>
          
          <!-- 图例 -->
          <div class="graph-legend">
            <h5>图例</h5>
            <div class="legend-items">
              <div v-for="nodeType in nodeTypes" :key="nodeType.type" class="legend-item">
                <div class="legend-color" :style="{ backgroundColor: nodeType.color }"></div>
                <span class="legend-label">{{ nodeType.label }}</span>
                <span class="legend-count">({{ nodeType.count }})</span>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 节点列表 -->
    <div class="nodes-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>节点列表</h3>
            <div class="nodes-controls">
              <el-input
                v-model="nodeSearchText"
                placeholder="搜索节点"
                size="small"
                style="width: 200px;"
                clearable
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              
              <el-select v-model="nodeTypeFilter" size="small" style="width: 120px; margin-left: 12px;" clearable placeholder="节点类型">
                <el-option label="全部" value="" />
                <el-option v-for="type in nodeTypes" :key="type.type" :label="type.label" :value="type.type" />
              </el-select>
            </div>
          </div>
        </template>
        
        <div class="nodes-list" v-loading="nodesLoading">
          <el-table :data="filteredNodes" stripe>
            <el-table-column prop="name" label="节点名称" min-width="150">
              <template #default="{ row }">
                <div class="node-name">
                  <div class="node-color" :style="{ backgroundColor: getNodeColor(row.type) }"></div>
                  <span>{{ row.name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ getNodeTypeLabel(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="degree" label="连接度" width="80" sortable />
            <el-table-column prop="createTime" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.createTime) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" text @click="viewNode(row.id)">
                  查看
                </el-button>
                <el-button size="small" text @click="highlightNode(row.id)">
                  高亮
                </el-button>
                <el-button size="small" text type="danger" @click="deleteNode(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="totalNodes"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 关系列表 -->
    <div class="edges-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>关系列表</h3>
            <div class="edges-controls">
              <el-input
                v-model="edgeSearchText"
                placeholder="搜索关系"
                size="small"
                style="width: 200px;"
                clearable
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              
              <el-select v-model="edgeTypeFilter" size="small" style="width: 120px; margin-left: 12px;" clearable placeholder="关系类型">
                <el-option label="全部" value="" />
                <el-option v-for="type in edgeTypes" :key="type" :label="type" :value="type" />
              </el-select>
            </div>
          </div>
        </template>
        
        <div class="edges-list" v-loading="edgesLoading">
          <el-table :data="filteredEdges" stripe>
            <el-table-column prop="source" label="源节点" min-width="120" />
            <el-table-column prop="type" label="关系类型" width="100">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="target" label="目标节点" min-width="120" />
            <el-table-column prop="weight" label="权重" width="80" sortable>
              <template #default="{ row }">
                <el-rate v-model="row.weight" disabled show-score text-color="#ff9900" />
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.createTime) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" text @click="highlightEdge(row.id)">
                  高亮
                </el-button>
                <el-button size="small" text type="danger" @click="deleteEdge(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="edgeCurrentPage"
              v-model:page-size="edgePageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="totalEdges"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleEdgeSizeChange"
              @current-change="handleEdgeCurrentChange"
            />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 统计信息 -->
    <div class="statistics-section">
      <el-card>
        <template #header>
          <h3>统计信息</h3>
        </template>
        
        <div class="statistics-content">
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon">
                  <el-icon><DataBoard /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ graphData.nodeCount }}</div>
                  <div class="stat-label">节点总数</div>
                </div>
              </div>
            </el-col>
            
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon">
                  <el-icon><Connection /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ graphData.edgeCount }}</div>
                  <div class="stat-label">关系总数</div>
                </div>
              </div>
            </el-col>
            
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon">
                  <el-icon><TrendCharts /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ graphData.density?.toFixed(3) || '0.000' }}</div>
                  <div class="stat-label">图密度</div>
                </div>
              </div>
            </el-col>
            
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon">
                  <el-icon><Histogram /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ graphData.avgDegree?.toFixed(1) || '0.0' }}</div>
                  <div class="stat-label">平均度数</div>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-card>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑图谱" width="600px">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="100px">
        <el-form-item label="图谱名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入图谱名称" />
        </el-form-item>
        <el-form-item label="图谱类型" prop="type">
          <el-select v-model="editForm.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="知识图谱" value="knowledge" />
            <el-option label="关系图谱" value="relation" />
            <el-option label="概念图谱" value="concept" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="访问权限" prop="permission">
          <el-select v-model="editForm.permission" placeholder="请选择权限" style="width: 100%">
            <el-option label="公开" value="public" />
            <el-option label="内部" value="internal" />
            <el-option label="私有" value="private" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveGraph" :loading="saving">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Download,
  Edit,
  ZoomIn,
  ZoomOut,
  Refresh,
  FullScreen,
  Share,
  Search,
  DataBoard,
  Connection,
  TrendCharts,
  Histogram
} from '@element-plus/icons-vue'

interface GraphData {
  id: string
  name: string
  type: string
  status: string
  description: string
  createTime: string
  updateTime: string
  creator: string
  permission: string
  nodeCount: number
  edgeCount: number
  density?: number
  avgDegree?: number
}

interface NodeData {
  id: string
  name: string
  type: string
  degree: number
  createTime: string
}

interface EdgeData {
  id: string
  source: string
  target: string
  type: string
  weight: number
  createTime: string
}

interface NodeType {
  type: string
  label: string
  color: string
  count: number
}

const route = useRoute()
const router = useRouter()

const graphId = route.params.id as string

const loading = ref(false)
const graphLoading = ref(false)
const nodesLoading = ref(false)
const edgesLoading = ref(false)
const saving = ref(false)

const editDialogVisible = ref(false)
const isFullscreen = ref(false)

const graphContainer = ref()
const editFormRef = ref()

const layoutType = ref('force')
const nodeSearchText = ref('')
const nodeTypeFilter = ref('')
const edgeSearchText = ref('')
const edgeTypeFilter = ref('')

const currentPage = ref(1)
const pageSize = ref(20)
const totalNodes = ref(0)

const edgeCurrentPage = ref(1)
const edgePageSize = ref(20)
const totalEdges = ref(0)

const graphData = ref<GraphData>({
  id: '',
  name: '',
  type: '',
  status: '',
  description: '',
  createTime: '',
  updateTime: '',
  creator: '',
  permission: '',
  nodeCount: 0,
  edgeCount: 0
})

const nodes = ref<NodeData[]>([])
const edges = ref<EdgeData[]>([])

const nodeTypes = ref<NodeType[]>([
  { type: 'person', label: '人物', color: '#409eff', count: 0 },
  { type: 'organization', label: '组织', color: '#67c23a', count: 0 },
  { type: 'location', label: '地点', color: '#e6a23c', count: 0 },
  { type: 'event', label: '事件', color: '#f56c6c', count: 0 },
  { type: 'concept', label: '概念', color: '#909399', count: 0 }
])

const edgeTypes = ref<string[]>(['属于', '关联', '包含', '依赖', '影响'])

const editForm = reactive({
  name: '',
  type: '',
  permission: '',
  description: ''
})

const editRules = {
  name: [
    { required: true, message: '请输入图谱名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择图谱类型', trigger: 'change' }
  ],
  permission: [
    { required: true, message: '请选择访问权限', trigger: 'change' }
  ]
}

// 过滤后的节点
const filteredNodes = computed(() => {
  let result = nodes.value
  
  if (nodeSearchText.value) {
    result = result.filter(node => 
      node.name.toLowerCase().includes(nodeSearchText.value.toLowerCase())
    )
  }
  
  if (nodeTypeFilter.value) {
    result = result.filter(node => node.type === nodeTypeFilter.value)
  }
  
  return result
})

// 过滤后的关系
const filteredEdges = computed(() => {
  let result = edges.value
  
  if (edgeSearchText.value) {
    result = result.filter(edge => 
      edge.source.toLowerCase().includes(edgeSearchText.value.toLowerCase()) ||
      edge.target.toLowerCase().includes(edgeSearchText.value.toLowerCase()) ||
      edge.type.toLowerCase().includes(edgeSearchText.value.toLowerCase())
    )
  }
  
  if (edgeTypeFilter.value) {
    result = result.filter(edge => edge.type === edgeTypeFilter.value)
  }
  
  return result
})

// 获取状态类型
const getStatusType = (status: string): string => {
  const typeMap: Record<string, string> = {
    'active': 'success',
    'inactive': 'warning',
    'building': 'info',
    'error': 'danger'
  }
  return typeMap[status] || 'info'
}

// 格式化日期
const formatDate = (dateString: string): string => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN')
}

// 获取节点颜色
const getNodeColor = (type: string): string => {
  const nodeType = nodeTypes.value.find(t => t.type === type)
  return nodeType?.color || '#909399'
}

// 获取节点类型标签
const getNodeTypeLabel = (type: string): string => {
  const nodeType = nodeTypes.value.find(t => t.type === type)
  return nodeType?.label || type
}

// 图谱操作
const zoomIn = () => {
  ElMessage.info('放大图谱')
}

const zoomOut = () => {
  ElMessage.info('缩小图谱')
}

const resetZoom = () => {
  ElMessage.info('重置缩放')
}

const changeLayout = () => {
  ElMessage.info(`切换到${layoutType.value}布局`)
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    document.documentElement.requestFullscreen?.()
  } else {
    document.exitFullscreen?.()
  }
}

// 导出图谱
const exportGraph = () => {
  ElMessage.success('开始导出图谱')
}

// 编辑图谱
const editGraph = () => {
  Object.assign(editForm, {
    name: graphData.value.name,
    type: graphData.value.type,
    permission: graphData.value.permission,
    description: graphData.value.description
  })
  editDialogVisible.value = true
}

// 保存图谱
const saveGraph = async () => {
  if (!editFormRef.value) return
  
  try {
    await editFormRef.value.validate()
    
    saving.value = true
    
    // 这里应该调用实际的API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    Object.assign(graphData.value, editForm)
    
    ElMessage.success('保存成功')
    editDialogVisible.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 节点操作
const viewNode = (id: string) => {
  router.push(`/knowledge/entities/detail/${id}`)
}

const highlightNode = (id: string) => {
  ElMessage.info(`高亮节点: ${id}`)
}

const deleteNode = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这个节点吗？', '确认删除', {
      type: 'warning'
    })
    
    ElMessage.success('删除成功')
    // 这里应该调用实际的删除API并刷新数据
  } catch (error) {
    // 用户取消删除
  }
}

// 关系操作
const highlightEdge = (id: string) => {
  ElMessage.info(`高亮关系: ${id}`)
}

const deleteEdge = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这个关系吗？', '确认删除', {
      type: 'warning'
    })
    
    ElMessage.success('删除成功')
    // 这里应该调用实际的删除API并刷新数据
  } catch (error) {
    // 用户取消删除
  }
}

// 分页处理
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  // 重新加载数据
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  // 重新加载数据
}

const handleEdgeSizeChange = (size: number) => {
  edgePageSize.value = size
  edgeCurrentPage.value = 1
  // 重新加载数据
}

const handleEdgeCurrentChange = (page: number) => {
  edgeCurrentPage.value = page
  // 重新加载数据
}

// 获取图谱详情
const fetchGraphDetail = async () => {
  try {
    loading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    graphData.value = {
      id: graphId,
      name: '企业知识图谱',
      type: 'knowledge',
      status: 'active',
      description: '包含企业组织架构、人员关系、项目信息等的综合知识图谱',
      createTime: '2024-01-15T10:30:00Z',
      updateTime: '2024-01-20T14:20:00Z',
      creator: '管理员',
      permission: 'internal',
      nodeCount: 156,
      edgeCount: 234,
      density: 0.019,
      avgDegree: 3.0
    }
    
    // 更新节点类型统计
    nodeTypes.value = [
      { type: 'person', label: '人物', color: '#409eff', count: 45 },
      { type: 'organization', label: '组织', color: '#67c23a', count: 23 },
      { type: 'location', label: '地点', color: '#e6a23c', count: 18 },
      { type: 'event', label: '事件', color: '#f56c6c', count: 32 },
      { type: 'concept', label: '概念', color: '#909399', count: 38 }
    ]
    
    totalNodes.value = graphData.value.nodeCount
    totalEdges.value = graphData.value.edgeCount
  } catch (error) {
    ElMessage.error('获取图谱详情失败')
  } finally {
    loading.value = false
  }
}

// 获取节点列表
const fetchNodes = async () => {
  try {
    nodesLoading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    nodes.value = [
      { id: '1', name: '张三', type: 'person', degree: 5, createTime: '2024-01-15T10:30:00Z' },
      { id: '2', name: '技术部', type: 'organization', degree: 12, createTime: '2024-01-15T10:30:00Z' },
      { id: '3', name: '北京', type: 'location', degree: 8, createTime: '2024-01-15T10:30:00Z' },
      { id: '4', name: '项目A', type: 'event', degree: 6, createTime: '2024-01-16T10:30:00Z' },
      { id: '5', name: '人工智能', type: 'concept', degree: 15, createTime: '2024-01-16T10:30:00Z' }
    ]
  } catch (error) {
    ElMessage.error('获取节点列表失败')
  } finally {
    nodesLoading.value = false
  }
}

// 获取关系列表
const fetchEdges = async () => {
  try {
    edgesLoading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    edges.value = [
      { id: '1', source: '张三', target: '技术部', type: '属于', weight: 4, createTime: '2024-01-15T10:30:00Z' },
      { id: '2', source: '张三', target: '项目A', type: '负责', weight: 5, createTime: '2024-01-16T10:30:00Z' },
      { id: '3', source: '技术部', target: '北京', type: '位于', weight: 3, createTime: '2024-01-15T10:30:00Z' },
      { id: '4', source: '项目A', target: '人工智能', type: '涉及', weight: 4, createTime: '2024-01-16T10:30:00Z' }
    ]
  } catch (error) {
    ElMessage.error('获取关系列表失败')
  } finally {
    edgesLoading.value = false
  }
}

// 监听全屏状态变化
const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => {
  fetchGraphDetail()
  fetchNodes()
  fetchEdges()
  
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})
</script>

<style scoped>
.graph-detail {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.detail-header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.breadcrumb {
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.graph-info-section,
.graph-visualization-section,
.nodes-section,
.edges-section,
.statistics-section {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-item .label {
  color: #909399;
  margin-right: 8px;
}

.info-item .value {
  color: #303133;
  font-weight: 500;
}

.graph-description h4 {
  margin: 0 0 8px 0;
  color: #303133;
}

.graph-description p {
  color: #606266;
  line-height: 1.6;
  margin: 0;
}

.visualization-controls {
  display: flex;
  align-items: center;
}

.graph-container {
  position: relative;
  height: 600px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}

.graph-canvas {
  width: 100%;
  height: 100%;
  background-color: #fafafa;
  position: relative;
}

.graph-canvas.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  background-color: #fff;
}

.graph-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #909399;
}

.graph-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.graph-stats {
  font-size: 14px;
  margin-top: 8px;
}

.graph-legend {
  position: absolute;
  top: 16px;
  right: 16px;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  min-width: 150px;
}

.graph-legend h5 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 14px;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-label {
  color: #303133;
}

.legend-count {
  color: #909399;
}

.nodes-controls,
.edges-controls {
  display: flex;
  align-items: center;
}

.node-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-color {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.statistics-content {
  padding: 20px 0;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #409eff;
  color: #fff;
  border-radius: 50%;
  font-size: 24px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .graph-detail {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .visualization-controls {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .graph-container {
    height: 400px;
  }
  
  .graph-legend {
    position: static;
    margin-top: 12px;
  }
  
  .nodes-controls,
  .edges-controls {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .statistics-content .el-row {
    flex-direction: column;
  }
  
  .stat-card {
    margin-bottom: 12px;
  }
}
</style>