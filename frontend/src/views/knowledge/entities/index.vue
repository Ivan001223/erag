<template>
  <div class="entities-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Collection /></el-icon>
            实体管理
          </h1>
          <p class="page-description">
            管理知识图谱中的实体信息，包括创建、编辑、删除和查看实体详情
          </p>
        </div>
        <div class="header-right">
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            创建实体
          </el-button>
          <el-button @click="showImportDialog">
            <el-icon><Upload /></el-icon>
            批量导入
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 搜索和筛选 -->
    <div class="search-section">
      <el-card shadow="never">
        <div class="search-form">
          <div class="search-row">
            <div class="search-item">
              <el-input
                v-model="searchForm.keyword"
                placeholder="搜索实体名称、描述或属性"
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
                v-model="searchForm.graphId"
                placeholder="选择知识图谱"
                clearable
                filterable
              >
                <el-option
                  v-for="graph in graphList"
                  :key="graph.id"
                  :label="graph.name"
                  :value="graph.id"
                />
              </el-select>
            </div>
            
            <div class="search-item">
              <el-select
                v-model="searchForm.type"
                placeholder="实体类型"
                clearable
                filterable
              >
                <el-option
                  v-for="type in entityTypes"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
            </div>
            
            <div class="search-item">
              <el-date-picker
                v-model="searchForm.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
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
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-checkbox
          v-model="selectAll"
          :indeterminate="isIndeterminate"
          @change="handleSelectAll"
        >
          全选
        </el-checkbox>
        <span class="selected-info" v-if="selectedEntities.length > 0">
          已选择 {{ selectedEntities.length }} 个实体
        </span>
      </div>
      
      <div class="toolbar-center">
        <el-button-group>
          <el-button
            :disabled="selectedEntities.length === 0"
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
          <el-button
            :disabled="selectedEntities.length === 0"
            @click="handleBatchExport"
          >
            <el-icon><Download /></el-icon>
            批量导出
          </el-button>
          <el-button
            :disabled="selectedEntities.length === 0"
            @click="handleBatchEdit"
          >
            <el-icon><Edit /></el-icon>
            批量编辑
          </el-button>
        </el-button-group>
      </div>
      
      <div class="toolbar-right">
        <el-button-group>
          <el-button @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button
            :type="viewMode === 'table' ? 'primary' : ''"
            @click="viewMode = 'table'"
          >
            <el-icon><List /></el-icon>
          </el-button>
          <el-button
            :type="viewMode === 'card' ? 'primary' : ''"
            @click="viewMode = 'card'"
          >
            <el-icon><Grid /></el-icon>
          </el-button>
          <el-button
            :type="viewMode === 'graph' ? 'primary' : ''"
            @click="viewMode = 'graph'"
          >
            <el-icon><Share /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <!-- 实体列表 -->
    <div class="entities-content">
      <!-- 表格视图 -->
      <el-card v-if="viewMode === 'table'" shadow="never">
        <el-table
          v-loading="loading"
          :data="entitiesList"
          @selection-change="handleSelectionChange"
          stripe
          style="width: 100%"
        >
          <el-table-column type="selection" width="55" />
          
          <el-table-column prop="name" label="实体名称" min-width="150">
            <template #default="{ row }">
              <div class="entity-name">
                <el-avatar
                  :size="32"
                  :style="{ backgroundColor: getTypeColor(row.type) }"
                >
                  {{ row.name.charAt(0) }}
                </el-avatar>
                <div class="name-info">
                  <div class="name">{{ row.name }}</div>
                  <div class="id">ID: {{ row.id }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag
                :type="getTypeTagType(row.type)"
                size="small"
              >
                {{ getTypeLabel(row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          
          <el-table-column prop="properties" label="属性" width="100">
            <template #default="{ row }">
              <el-tag size="small" type="info">
                {{ Object.keys(row.properties || {}).length }} 个
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="relations" label="关系" width="100">
            <template #default="{ row }">
              <el-tag size="small" type="warning">
                {{ row.relationCount || 0 }} 个
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="graphName" label="所属图谱" width="120" show-overflow-tooltip />
          
          <el-table-column prop="createdAt" label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.createdAt) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button-group>
                <el-button size="small" @click="viewEntity(row)">
                  <el-icon><View /></el-icon>
                </el-button>
                <el-button size="small" @click="editEntity(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" @click="viewRelations(row)">
                  <el-icon><Share /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  @click="deleteEntity(row)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
      
      <!-- 卡片视图 -->
      <div v-else-if="viewMode === 'card'" class="card-view">
        <div v-loading="loading" class="cards-grid">
          <div
            v-for="entity in entitiesList"
            :key="entity.id"
            class="entity-card"
            :class="{ selected: selectedEntities.includes(entity.id) }"
            @click="toggleSelection(entity)"
          >
            <el-card shadow="hover">
              <div class="card-header">
                <div class="entity-avatar">
                  <el-avatar
                    :size="48"
                    :style="{ backgroundColor: getTypeColor(entity.type) }"
                  >
                    {{ entity.name.charAt(0) }}
                  </el-avatar>
                </div>
                <div class="entity-info">
                  <h3 class="entity-name">{{ entity.name }}</h3>
                  <el-tag
                    :type="getTypeTagType(entity.type)"
                    size="small"
                  >
                    {{ getTypeLabel(entity.type) }}
                  </el-tag>
                </div>
                <div class="card-actions">
                  <el-checkbox
                    :model-value="selectedEntities.includes(entity.id)"
                    @change="toggleSelection(entity)"
                    @click.stop
                  />
                </div>
              </div>
              
              <div class="card-content">
                <p class="description">{{ entity.description || '暂无描述' }}</p>
                
                <div class="stats">
                  <div class="stat-item">
                    <span class="label">属性：</span>
                    <span class="value">{{ Object.keys(entity.properties || {}).length }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">关系：</span>
                    <span class="value">{{ entity.relationCount || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">图谱：</span>
                    <span class="value">{{ entity.graphName }}</span>
                  </div>
                </div>
                
                <div class="properties" v-if="entity.properties">
                  <div class="properties-title">主要属性：</div>
                  <div class="properties-list">
                    <el-tag
                      v-for="(value, key) in getMainProperties(entity.properties)"
                      :key="key"
                      size="small"
                      class="property-tag"
                    >
                      {{ key }}: {{ value }}
                    </el-tag>
                  </div>
                </div>
              </div>
              
              <div class="card-footer">
                <div class="time-info">
                  <el-icon><Clock /></el-icon>
                  <span>{{ formatDate(entity.createdAt) }}</span>
                </div>
                <div class="actions">
                  <el-button size="small" @click.stop="viewEntity(entity)">
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button size="small" @click.stop="editEntity(entity)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button size="small" @click.stop="viewRelations(entity)">
                    <el-icon><Share /></el-icon>
                  </el-button>
                  <el-button
                    size="small"
                    type="danger"
                    @click.stop="deleteEntity(entity)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>
        </div>
      </div>
      
      <!-- 图谱视图 -->
      <div v-else-if="viewMode === 'graph'" class="graph-view">
        <el-card shadow="never">
          <div class="graph-container" ref="graphContainer">
            <!-- 这里将集成图谱可视化组件 -->
            <div class="graph-placeholder">
              <el-icon><Share /></el-icon>
              <p>图谱可视化视图</p>
              <p class="sub-text">显示实体之间的关系网络</p>
            </div>
          </div>
        </el-card>
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
        @current-change="handleCurrentChange"
      />
    </div>
    
    <!-- 创建/编辑实体对话框 -->
    <el-dialog
      v-model="entityDialogVisible"
      :title="isEdit ? '编辑实体' : '创建实体'"
      width="800px"
      :before-close="handleEntityDialogClose"
    >
      <el-form
        ref="entityFormRef"
        :model="entityForm"
        :rules="entityRules"
        label-width="100px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="实体名称" prop="name">
              <el-input v-model="entityForm.name" placeholder="请输入实体名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="实体类型" prop="type">
              <el-select
                v-model="entityForm.type"
                placeholder="请选择实体类型"
                filterable
                allow-create
              >
                <el-option
                  v-for="type in entityTypes"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所属图谱" prop="graphId">
              <el-select
                v-model="entityForm.graphId"
                placeholder="请选择知识图谱"
                filterable
              >
                <el-option
                  v-for="graph in graphList"
                  :key="graph.id"
                  :label="graph.name"
                  :value="graph.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-switch
                v-model="entityForm.active"
                active-text="启用"
                inactive-text="禁用"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="描述">
          <el-input
            v-model="entityForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入实体描述"
          />
        </el-form-item>
        
        <el-form-item label="属性">
          <div class="properties-editor">
            <div
              v-for="(property, index) in entityForm.properties"
              :key="index"
              class="property-item"
            >
              <el-input
                v-model="property.key"
                placeholder="属性名"
                style="width: 200px; margin-right: 10px;"
              />
              <el-select
                v-model="property.type"
                placeholder="类型"
                style="width: 120px; margin-right: 10px;"
              >
                <el-option label="文本" value="string" />
                <el-option label="数字" value="number" />
                <el-option label="日期" value="date" />
                <el-option label="布尔" value="boolean" />
                <el-option label="JSON" value="json" />
              </el-select>
              <el-input
                v-model="property.value"
                placeholder="属性值"
                style="flex: 1; margin-right: 10px;"
              />
              <el-button
                type="danger"
                size="small"
                @click="removeProperty(index)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button
              type="primary"
              size="small"
              @click="addProperty"
              style="margin-top: 10px;"
            >
              <el-icon><Plus /></el-icon>
              添加属性
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item label="标签">
          <el-select
            v-model="entityForm.tags"
            multiple
            filterable
            allow-create
            placeholder="请选择或输入标签"
            style="width: 100%"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="entityDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleEntitySubmit" :loading="submitting">
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 实体详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="实体详情"
      width="900px"
    >
      <div v-if="currentEntity" class="entity-detail">
        <div class="detail-header">
          <el-avatar
            :size="64"
            :style="{ backgroundColor: getTypeColor(currentEntity.type) }"
          >
            {{ currentEntity.name.charAt(0) }}
          </el-avatar>
          <div class="header-info">
            <h2>{{ currentEntity.name }}</h2>
            <div class="meta-info">
              <el-tag :type="getTypeTagType(currentEntity.type)">
                {{ getTypeLabel(currentEntity.type) }}
              </el-tag>
              <span class="id">ID: {{ currentEntity.id }}</span>
              <span class="graph">图谱: {{ currentEntity.graphName }}</span>
            </div>
          </div>
        </div>
        
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <div class="basic-info">
              <div class="info-item">
                <span class="label">描述：</span>
                <span class="value">{{ currentEntity.description || '暂无描述' }}</span>
              </div>
              <div class="info-item">
                <span class="label">创建时间：</span>
                <span class="value">{{ formatDate(currentEntity.createdAt) }}</span>
              </div>
              <div class="info-item">
                <span class="label">更新时间：</span>
                <span class="value">{{ formatDate(currentEntity.updatedAt) }}</span>
              </div>
              <div class="info-item">
                <span class="label">创建者：</span>
                <span class="value">{{ currentEntity.createdBy || '系统' }}</span>
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="属性" name="properties">
            <div class="properties-detail">
              <el-table
                :data="formatProperties(currentEntity.properties)"
                stripe
              >
                <el-table-column prop="key" label="属性名" width="200" />
                <el-table-column prop="type" label="类型" width="100">
                  <template #default="{ row }">
                    <el-tag size="small">{{ row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="value" label="值" show-overflow-tooltip />
              </el-table>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="关系" name="relations">
            <div class="relations-detail">
              <!-- 关系列表将在这里显示 -->
              <p>关系信息加载中...</p>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="标签" name="tags">
            <div class="tags-detail">
              <el-tag
                v-for="tag in currentEntity.tags"
                :key="tag"
                class="tag-item"
              >
                {{ tag }}
              </el-tag>
              <span v-if="!currentEntity.tags || currentEntity.tags.length === 0">
                暂无标签
              </span>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  Plus,
  Upload,
  Search,
  Refresh,
  Delete,
  Download,
  Edit,
  List,
  Grid,
  Share,
  View,
  Clock
} from '@element-plus/icons-vue'
import { format } from 'date-fns'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const viewMode = ref('table') // table, card, graph
const selectAll = ref(false)
const selectedEntities = ref<string[]>([])
const entityDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const isEdit = ref(false)
const currentEntity = ref(null)
const activeTab = ref('basic')
const entityFormRef = ref()

// 搜索表单
const searchForm = reactive({
  keyword: '',
  graphId: '',
  type: '',
  dateRange: []
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 实体表单
const entityForm = reactive({
  id: '',
  name: '',
  type: '',
  graphId: '',
  description: '',
  properties: [],
  tags: [],
  active: true
})

// 表单验证规则
const entityRules = {
  name: [
    { required: true, message: '请输入实体名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择实体类型', trigger: 'change' }
  ],
  graphId: [
    { required: true, message: '请选择知识图谱', trigger: 'change' }
  ]
}

// 模拟数据
const entitiesList = ref([
  {
    id: '1',
    name: '张三',
    type: 'person',
    description: '软件工程师，专注于前端开发',
    properties: {
      age: '28',
      gender: '男',
      email: 'zhangsan@example.com',
      department: '技术部'
    },
    relationCount: 5,
    graphId: 'graph1',
    graphName: '员工关系图谱',
    tags: ['员工', '技术'],
    createdAt: '2024-01-15T10:30:00Z',
    updatedAt: '2024-01-20T14:20:00Z',
    createdBy: 'admin'
  },
  {
    id: '2',
    name: 'Vue.js',
    type: 'technology',
    description: '渐进式JavaScript框架',
    properties: {
      version: '3.4.0',
      type: 'framework',
      language: 'JavaScript',
      license: 'MIT'
    },
    relationCount: 12,
    graphId: 'graph2',
    graphName: '技术栈图谱',
    tags: ['前端', '框架'],
    createdAt: '2024-01-10T09:15:00Z',
    updatedAt: '2024-01-18T16:45:00Z',
    createdBy: 'system'
  }
])

const graphList = ref([
  { id: 'graph1', name: '员工关系图谱' },
  { id: 'graph2', name: '技术栈图谱' },
  { id: 'graph3', name: '产品知识图谱' }
])

const entityTypes = ref([
  { label: '人员', value: 'person' },
  { label: '组织', value: 'organization' },
  { label: '技术', value: 'technology' },
  { label: '产品', value: 'product' },
  { label: '概念', value: 'concept' },
  { label: '事件', value: 'event' },
  { label: '地点', value: 'location' }
])

const availableTags = ref([
  '员工', '技术', '前端', '后端', '框架', '工具', '产品', '服务'
])

// 计算属性
const isIndeterminate = computed(() => {
  const selected = selectedEntities.value.length
  const total = entitiesList.value.length
  return selected > 0 && selected < total
})

// 方法
const formatDate = (dateString: string) => {
  return format(new Date(dateString), 'yyyy-MM-dd HH:mm')
}

const getTypeColor = (type: string) => {
  const colors = {
    person: '#409eff',
    organization: '#67c23a',
    technology: '#e6a23c',
    product: '#f56c6c',
    concept: '#909399',
    event: '#c71585',
    location: '#20b2aa'
  }
  return colors[type] || '#909399'
}

const getTypeTagType = (type: string) => {
  const types = {
    person: 'primary',
    organization: 'success',
    technology: 'warning',
    product: 'danger',
    concept: 'info',
    event: 'primary',
    location: 'success'
  }
  return types[type] || 'info'
}

const getTypeLabel = (type: string) => {
  const typeObj = entityTypes.value.find(t => t.value === type)
  return typeObj ? typeObj.label : type
}

const getMainProperties = (properties: any) => {
  if (!properties) return {}
  const keys = Object.keys(properties)
  const mainKeys = keys.slice(0, 3) // 只显示前3个属性
  const result = {}
  mainKeys.forEach(key => {
    result[key] = properties[key]
  })
  return result
}

const formatProperties = (properties: any) => {
  if (!properties) return []
  return Object.entries(properties).map(([key, value]) => ({
    key,
    value: String(value),
    type: typeof value === 'number' ? 'number' : 
          typeof value === 'boolean' ? 'boolean' :
          value instanceof Date ? 'date' : 'string'
  }))
}

// 搜索和筛选
const handleSearch = () => {
  pagination.page = 1
  loadEntities()
}

const handleReset = () => {
  Object.assign(searchForm, {
    keyword: '',
    graphId: '',
    type: '',
    dateRange: []
  })
  handleSearch()
}

// 选择操作
const handleSelectAll = (checked: boolean) => {
  if (checked) {
    selectedEntities.value = entitiesList.value.map(item => item.id)
  } else {
    selectedEntities.value = []
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedEntities.value = selection.map(item => item.id)
  selectAll.value = selection.length === entitiesList.value.length
}

const toggleSelection = (entity: any) => {
  const index = selectedEntities.value.indexOf(entity.id)
  if (index > -1) {
    selectedEntities.value.splice(index, 1)
  } else {
    selectedEntities.value.push(entity.id)
  }
  selectAll.value = selectedEntities.value.length === entitiesList.value.length
}

// 批量操作
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedEntities.value.length} 个实体吗？`,
      '批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里调用删除API
    ElMessage.success('删除成功')
    selectedEntities.value = []
    loadEntities()
    
  } catch (error) {
    // 用户取消
  }
}

const handleBatchExport = () => {
  ElMessage.info('导出功能开发中...')
}

const handleBatchEdit = () => {
  ElMessage.info('批量编辑功能开发中...')
}

// 刷新
const handleRefresh = () => {
  loadEntities()
}

// 分页
const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  loadEntities()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadEntities()
}

// 实体操作
const showCreateDialog = () => {
  isEdit.value = false
  resetEntityForm()
  entityDialogVisible.value = true
}

const showImportDialog = () => {
  ElMessage.info('批量导入功能开发中...')
}

const viewEntity = (entity: any) => {
  currentEntity.value = entity
  activeTab.value = 'basic'
  detailDialogVisible.value = true
}

const editEntity = (entity: any) => {
  isEdit.value = true
  Object.assign(entityForm, {
    ...entity,
    properties: Object.entries(entity.properties || {}).map(([key, value]) => ({
      key,
      value: String(value),
      type: typeof value === 'number' ? 'number' : 
            typeof value === 'boolean' ? 'boolean' :
            value instanceof Date ? 'date' : 'string'
    }))
  })
  entityDialogVisible.value = true
}

const deleteEntity = async (entity: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除实体 "${entity.name}" 吗？`,
      '删除实体',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里调用删除API
    ElMessage.success('删除成功')
    loadEntities()
    
  } catch (error) {
    // 用户取消
  }
}

const viewRelations = (entity: any) => {
  router.push(`/knowledge/relations?entityId=${entity.id}`)
}

// 表单操作
const resetEntityForm = () => {
  Object.assign(entityForm, {
    id: '',
    name: '',
    type: '',
    graphId: '',
    description: '',
    properties: [],
    tags: [],
    active: true
  })
  entityFormRef.value?.clearValidate()
}

const handleEntityDialogClose = () => {
  resetEntityForm()
  entityDialogVisible.value = false
}

const addProperty = () => {
  entityForm.properties.push({
    key: '',
    value: '',
    type: 'string'
  })
}

const removeProperty = (index: number) => {
  entityForm.properties.splice(index, 1)
}

const handleEntitySubmit = async () => {
  try {
    await entityFormRef.value.validate()
    
    submitting.value = true
    
    // 转换属性格式
    const properties = {}
    entityForm.properties.forEach(prop => {
      if (prop.key && prop.value) {
        let value = prop.value
        if (prop.type === 'number') {
          value = Number(value)
        } else if (prop.type === 'boolean') {
          value = value === 'true'
        } else if (prop.type === 'json') {
          try {
            value = JSON.parse(value)
          } catch (e) {
            // 保持原值
          }
        }
        properties[prop.key] = value
      }
    })
    
    const submitData = {
      ...entityForm,
      properties
    }
    
    // 这里调用创建或更新API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    entityDialogVisible.value = false
    loadEntities()
    
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitting.value = false
  }
}

// 数据加载
const loadEntities = async () => {
  try {
    loading.value = true
    
    // 这里调用获取实体列表的API
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟分页数据
    pagination.total = 50
    
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 页面初始化
onMounted(() => {
  loadEntities()
})
</script>

<style lang="scss" scoped>
.entities-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 20px;
  
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
    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: #2c3e50;
      margin: 0 0 8px 0;
      
      .el-icon {
        color: #409eff;
      }
    }
    
    .page-description {
      color: #6c757d;
      margin: 0;
      font-size: 14px;
    }
  }
  
  .header-right {
    display: flex;
    gap: 12px;
  }
}

.search-section {
  margin-bottom: 20px;
  
  .search-form {
    .search-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
      flex-wrap: wrap;
      
      .search-item {
        min-width: 200px;
        flex: 1;
      }
    }
    
    .search-actions {
      display: flex;
      gap: 12px;
    }
  }
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  
  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .selected-info {
      color: #409eff;
      font-size: 14px;
    }
  }
  
  .toolbar-center {
    flex: 1;
    display: flex;
    justify-content: center;
  }
  
  .toolbar-right {
    display: flex;
    gap: 12px;
  }
}

.entities-content {
  margin-bottom: 20px;
}

// 表格视图样式
.entity-name {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .name-info {
    .name {
      font-weight: 500;
      color: #2c3e50;
    }
    
    .id {
      font-size: 12px;
      color: #6c757d;
    }
  }
}

// 卡片视图样式
.card-view {
  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 20px;
  }
  
  .entity-card {
    cursor: pointer;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
    }
    
    &.selected {
      .el-card {
        border-color: #409eff;
        box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
      }
    }
    
    .card-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      
      .entity-avatar {
        flex-shrink: 0;
      }
      
      .entity-info {
        flex: 1;
        
        .entity-name {
          margin: 0 0 8px 0;
          font-size: 16px;
          font-weight: 600;
          color: #2c3e50;
        }
      }
      
      .card-actions {
        flex-shrink: 0;
      }
    }
    
    .card-content {
      .description {
        color: #6c757d;
        font-size: 14px;
        line-height: 1.5;
        margin: 0 0 16px 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      
      .stats {
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
        
        .stat-item {
          font-size: 12px;
          
          .label {
            color: #6c757d;
          }
          
          .value {
            color: #2c3e50;
            font-weight: 500;
          }
        }
      }
      
      .properties {
        .properties-title {
          font-size: 12px;
          color: #6c757d;
          margin-bottom: 8px;
        }
        
        .properties-list {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          
          .property-tag {
            font-size: 11px;
          }
        }
      }
    }
    
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid #ebeef5;
      
      .time-info {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        color: #6c757d;
      }
      
      .actions {
        display: flex;
        gap: 4px;
      }
    }
  }
}

// 图谱视图样式
.graph-view {
  .graph-container {
    height: 600px;
    position: relative;
    
    .graph-placeholder {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #6c757d;
      
      .el-icon {
        font-size: 64px;
        margin-bottom: 16px;
      }
      
      p {
        margin: 0;
        font-size: 16px;
        
        &.sub-text {
          font-size: 14px;
          margin-top: 8px;
        }
      }
    }
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

// 对话框样式
.properties-editor {
  .property-item {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
  }
}

.entity-detail {
  .detail-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #ebeef5;
    
    .header-info {
      flex: 1;
      
      h2 {
        margin: 0 0 8px 0;
        color: #2c3e50;
      }
      
      .meta-info {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        
        .id, .graph {
          color: #6c757d;
        }
      }
    }
  }
  
  .basic-info {
    .info-item {
      display: flex;
      margin-bottom: 12px;
      
      .label {
        min-width: 80px;
        color: #6c757d;
        font-size: 14px;
      }
      
      .value {
        color: #2c3e50;
        font-size: 14px;
      }
    }
  }
  
  .tags-detail {
    .tag-item {
      margin-right: 8px;
      margin-bottom: 8px;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .entities-page {
    padding: 16px;
  }
  
  .page-header .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .toolbar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
    
    .toolbar-left,
    .toolbar-center,
    .toolbar-right {
      justify-content: center;
    }
  }
  
  .search-form .search-row {
    flex-direction: column;
    
    .search-item {
      min-width: auto;
    }
  }
  
  .cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>