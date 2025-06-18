<template>
  <div class="knowledge-graphs">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">知识图谱管理</h1>
        <p class="page-description">管理和查看所有知识图谱</p>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="createGraph">
          <el-icon><Plus /></el-icon>
          创建图谱
        </el-button>
      </div>
    </div>
    
    <!-- 搜索和筛选 -->
    <div class="search-section">
      <el-card>
        <el-form :model="searchForm" inline>
          <el-form-item label="图谱名称">
            <el-input
              v-model="searchForm.name"
              placeholder="请输入图谱名称"
              clearable
              style="width: 200px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          
          <el-form-item label="状态">
            <el-select
              v-model="searchForm.status"
              placeholder="请选择状态"
              clearable
              style="width: 120px"
            >
              <el-option label="全部" value="" />
              <el-option label="活跃" value="active" />
              <el-option label="草稿" value="draft" />
              <el-option label="已归档" value="archived" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="创建时间">
            <el-date-picker
              v-model="searchForm.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 240px"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="handleReset">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
    
    <!-- 图谱列表 -->
    <div class="graphs-section">
      <el-card>
        <!-- 工具栏 -->
        <div class="toolbar">
          <div class="toolbar-left">
            <el-button 
              type="danger" 
              :disabled="selectedGraphs.length === 0"
              @click="batchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除
            </el-button>
            <el-button 
              :disabled="selectedGraphs.length === 0"
              @click="batchExport"
            >
              <el-icon><Download /></el-icon>
              批量导出
            </el-button>
          </div>
          
          <div class="toolbar-right">
            <el-tooltip content="刷新">
              <el-button circle @click="loadGraphs">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </el-tooltip>
            
            <el-tooltip content="列表视图">
              <el-button 
                circle 
                :type="viewMode === 'list' ? 'primary' : 'default'"
                @click="viewMode = 'list'"
              >
                <el-icon><List /></el-icon>
              </el-button>
            </el-tooltip>
            
            <el-tooltip content="卡片视图">
              <el-button 
                circle 
                :type="viewMode === 'card' ? 'primary' : 'default'"
                @click="viewMode = 'card'"
              >
                <el-icon><Grid /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>
        
        <!-- 列表视图 -->
        <el-table
          v-if="viewMode === 'list'"
          :data="graphs"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          stripe
        >
          <el-table-column type="selection" width="55" />
          
          <el-table-column prop="name" label="图谱名称" min-width="200">
            <template #default="{ row }">
              <div class="graph-name">
                <el-icon class="graph-icon"><Share /></el-icon>
                <el-button type="primary" link @click="viewGraph(row)">
                  {{ row.name }}
                </el-button>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          
          <el-table-column prop="statistics.entityCount" label="实体数量" width="100" align="center">
            <template #default="{ row }">
              <el-tag type="info" size="small">{{ row.statistics.entityCount }}</el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="statistics.relationCount" label="关系数量" width="100" align="center">
            <template #default="{ row }">
              <el-tag type="success" size="small">{{ row.statistics.relationCount }}</el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="createdBy" label="创建者" width="120" />
          
          <el-table-column prop="metadata.createdAt" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(new Date(row.metadata.createdAt)) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="viewGraph(row)">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button type="primary" link @click="editGraph(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button type="danger" link @click="deleteGraph(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 卡片视图 -->
        <div v-else class="graphs-grid" v-loading="loading">
          <div 
            class="graph-card" 
            v-for="graph in graphs" 
            :key="graph.id"
            @click="viewGraph(graph)"
          >
            <div class="card-header">
              <div class="card-title">
                <el-icon class="graph-icon"><Share /></el-icon>
                <span>{{ graph.name }}</span>
              </div>
              <el-dropdown @command="handleCardAction">
                <el-button circle size="small">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="{ action: 'view', graph }">
                      <el-icon><View /></el-icon>
                      查看详情
                    </el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'edit', graph }">
                      <el-icon><Edit /></el-icon>
                      编辑图谱
                    </el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'export', graph }">
                      <el-icon><Download /></el-icon>
                      导出图谱
                    </el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'delete', graph }" divided>
                      <el-icon><Delete /></el-icon>
                      删除图谱
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            
            <div class="card-content">
              <p class="card-description">{{ graph.description || '暂无描述' }}</p>
              
              <div class="card-stats">
                <div class="stat-item">
                  <span class="stat-label">实体</span>
                  <span class="stat-value">{{ graph.entities.length }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">关系</span>
                  <span class="stat-value">{{ graph.relations.length }}</span>
                </div>
              </div>
            </div>
            
            <div class="card-footer">
              <div class="card-meta">
                <el-tag :type="getStatusType(graph.status || 'unknown')" size="small">
                  {{ getStatusText(graph.status || 'unknown') }}
                </el-tag>
                <span class="created-time">{{ formatDate(new Date(graph.metadata.createdAt)) }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.size"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Search, Refresh, Delete, Download, List, Grid,
  Share, View, Edit, MoreFilled
} from '@element-plus/icons-vue'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import type { KnowledgeGraph } from '@/types/knowledge'

const router = useRouter()

// 视图模式
const viewMode = ref<'list' | 'card'>('list')

// 加载状态
const loading = ref(false)

// 选中的图谱
const selectedGraphs = ref<KnowledgeGraph[]>([])

// 搜索表单
const searchForm = reactive({
  name: '',
  status: '',
  dateRange: null as [string, string] | null
})

// 分页信息
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 图谱列表
const graphs = ref<KnowledgeGraph[]>([])

// 模拟数据
const mockGraphs: KnowledgeGraph[] = [
  {
    id: '1',
    name: '企业组织架构图谱',
    description: '包含公司组织结构、人员关系和部门信息的知识图谱',
    entities: [],
    relations: [],
    documents: [],
    metadata: {
      createdAt: new Date('2024-01-15').toISOString(),
      updatedAt: new Date('2024-01-20').toISOString(),
      createdBy: '张三',
      version: '1.0',
      isPublic: false,
      tags: []
    },
    statistics: {
      entityCount: 1245,
      relationCount: 2890,
      documentCount: 0,
      typeDistribution: {} as any, // Cast to any to avoid enum key issues in mock
      relationTypeDistribution: {} as any // Cast to any to avoid enum key issues in mock
    },
    settings: {
      layout: 'force',
      physics: false,
      clustering: false,
      filtering: { entityTypes: [], relationTypes: [], minConfidence: 0, maxNodes: 0 }
    },
    status: 'active'
  },
  {
    id: '2',
    name: '产品技术图谱',
    description: '产品线、技术栈和依赖关系的知识图谱',
    entities: [],
    relations: [],
    documents: [],
    metadata: {
      createdAt: new Date('2024-01-10').toISOString(),
      updatedAt: new Date('2024-01-18').toISOString(),
      createdBy: '李四',
      version: '1.0',
      isPublic: false,
      tags: []
    },
    statistics: {
      entityCount: 856,
      relationCount: 1567,
      documentCount: 0,
      typeDistribution: {} as any,
      relationTypeDistribution: {} as any
    },
    settings: {
      layout: 'force',
      physics: false,
      clustering: false,
      filtering: { entityTypes: [], relationTypes: [], minConfidence: 0, maxNodes: 0 }
    },
    status: 'active'
  },
  {
    id: '3',
    name: '客户关系图谱',
    description: '客户信息、合作关系和业务往来的知识图谱',
    entities: [],
    relations: [],
    documents: [],
    metadata: {
      createdAt: new Date('2024-01-05').toISOString(),
      updatedAt: new Date('2024-01-15').toISOString(),
      createdBy: '王五',
      version: '1.0',
      isPublic: false,
      tags: []
    },
    statistics: {
      entityCount: 2134,
      relationCount: 4567,
      documentCount: 0,
      typeDistribution: {} as any,
      relationTypeDistribution: {} as any
    },
    settings: {
      layout: 'force',
      physics: false,
      clustering: false,
      filtering: { entityTypes: [], relationTypes: [], minConfidence: 0, maxNodes: 0 }
    },
    status: 'draft'
  }
]

// 获取状态类型
const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    active: 'success',
    draft: 'warning',
    archived: 'info'
  }
  return statusMap[status] || 'default'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    active: '活跃',
    draft: '草稿',
    archived: '已归档'
  }
  return statusMap[status] || status
}

// 格式化日期
const formatDate = (date: Date) => {
  return format(date, 'yyyy-MM-dd HH:mm', { locale: zhCN })
}

// 加载图谱列表
const loadGraphs = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用搜索过滤
    let filteredGraphs = [...mockGraphs]
    
    if (searchForm.name) {
      filteredGraphs = filteredGraphs.filter(graph => 
        graph.name.toLowerCase().includes(searchForm.name.toLowerCase())
      )
    }
    
    if (searchForm.status) {
      filteredGraphs = filteredGraphs.filter(graph => 
        graph.status === searchForm.status
      )
    }
    
    // 分页
    const start = (pagination.page - 1) * pagination.size
    const end = start + pagination.size
    
    graphs.value = filteredGraphs.slice(start, end)
    pagination.total = filteredGraphs.length
    
  } catch (error) {
    console.error('Load graphs error:', error)
    ElMessage.error('加载图谱列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadGraphs()
}

// 重置搜索
const handleReset = () => {
  searchForm.name = ''
  searchForm.status = ''
  searchForm.dateRange = null
  pagination.page = 1
  loadGraphs()
}

// 选择变化
const handleSelectionChange = (selection: KnowledgeGraph[]) => {
  selectedGraphs.value = selection
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  loadGraphs()
}

// 页码变化
const handlePageChange = (page: number) => {
  pagination.page = page
  loadGraphs()
}

// 创建图谱
const createGraph = () => {
  router.push('/knowledge/graphs/create')
}

// 查看图谱
const viewGraph = (graph: KnowledgeGraph) => {
  router.push(`/knowledge/graphs/${graph.id}`)
}

// 编辑图谱
const editGraph = (graph: KnowledgeGraph) => {
  router.push(`/knowledge/graphs/${graph.id}/edit`)
}

// 删除图谱
const deleteGraph = async (graph: KnowledgeGraph) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除图谱"${graph.name}"吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用删除API
    ElMessage.success('删除成功')
    loadGraphs()
    
  } catch (error) {
    // 用户取消删除
  }
}

// 批量删除
const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedGraphs.value.length} 个图谱吗？此操作不可恢复。`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用批量删除API
    ElMessage.success('批量删除成功')
    selectedGraphs.value = []
    loadGraphs()
    
  } catch (error) {
    // 用户取消删除
  }
}

// 批量导出
const batchExport = () => {
  ElMessage.info('批量导出功能开发中...')
}

// 卡片操作
const handleCardAction = (command: { action: string; graph: KnowledgeGraph }) => {
  const { action, graph } = command
  
  switch (action) {
    case 'view':
      viewGraph(graph)
      break
    case 'edit':
      editGraph(graph)
      break
    case 'export':
      ElMessage.info('导出功能开发中...')
      break
    case 'delete':
      deleteGraph(graph)
      break
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadGraphs()
})
</script>

<style lang="scss" scoped>
.knowledge-graphs {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  
  .header-left {
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
}

.search-section {
  margin-bottom: 16px;
}

.graphs-section {
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .toolbar-right {
      display: flex;
      gap: 8px;
    }
  }
  
  .graph-name {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .graph-icon {
      color: var(--el-color-primary);
    }
  }
  
  .graphs-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }
  
  .graph-card {
    border: 1px solid var(--el-border-color-light);
    border-radius: 8px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.3s;
    
    &:hover {
      border-color: var(--el-color-primary);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      transform: translateY(-2px);
    }
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      
      .card-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        color: var(--el-text-color-primary);
        
        .graph-icon {
          color: var(--el-color-primary);
        }
      }
    }
    
    .card-content {
      margin-bottom: 16px;
      
      .card-description {
        font-size: 14px;
        color: var(--el-text-color-regular);
        line-height: 1.5;
        margin: 0 0 12px 0;
        display: -webkit-box;
        text-overflow: ellipsis;
        -webkit-line-clamp: 2; /* autoprefixer: ignore next */
        line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      
      .card-stats {
        display: flex;
        gap: 24px;
        
        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          
          .stat-label {
            font-size: 12px;
            color: var(--el-text-color-secondary);
            margin-bottom: 4px;
          }
          
          .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }
        }
      }
    }
    
    .card-footer {
      .card-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        
        .created-time {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }
    }
  }
  
  .pagination-wrapper {
    display: flex;
    justify-content: center;
    margin-top: 24px;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .toolbar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .graphs-grid {
    grid-template-columns: 1fr;
  }
}
</style>