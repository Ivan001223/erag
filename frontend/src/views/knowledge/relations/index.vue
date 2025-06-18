<template>
  <div class="relations-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Share /></el-icon>
            关系管理
          </h1>
          <p class="page-description">
            管理知识图谱中实体之间的关系，包括创建、编辑、删除和查看关系详情
          </p>
        </div>
        <div class="header-right">
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            创建关系
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
                placeholder="搜索关系名称、描述或属性"
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
                placeholder="关系类型"
                clearable
                filterable
              >
                <el-option
                  v-for="type in relationTypes"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
            </div>
            
            <div class="search-item">
              <el-input
                v-model="searchForm.sourceEntity"
                placeholder="源实体"
                clearable
              />
            </div>
            
            <div class="search-item">
              <el-input
                v-model="searchForm.targetEntity"
                placeholder="目标实体"
                clearable
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
        <span class="selected-info" v-if="selectedRelations.length > 0">
          已选择 {{ selectedRelations.length }} 个关系
        </span>
      </div>
      
      <div class="toolbar-center">
        <el-button-group>
          <el-button
            :disabled="selectedRelations.length === 0"
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
          <el-button
            :disabled="selectedRelations.length === 0"
            @click="handleBatchExport"
          >
            <el-icon><Download /></el-icon>
            批量导出
          </el-button>
          <el-button
            :disabled="selectedRelations.length === 0"
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
    
    <!-- 关系列表 -->
    <div class="relations-content">
      <!-- 表格视图 -->
      <el-card v-if="viewMode === 'table'" shadow="never">
        <el-table
          v-loading="loading"
          :data="relationsList"
          @selection-change="handleSelectionChange"
          stripe
          style="width: 100%"
        >
          <el-table-column type="selection" width="55" />
          
          <el-table-column prop="name" label="关系名称" min-width="150">
            <template #default="{ row }">
              <div class="relation-name">
                <el-icon :style="{ color: getTypeColor(row.type) }">
                  <component :is="getTypeIcon(row.type)" />
                </el-icon>
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
          
          <el-table-column label="源实体" min-width="150">
            <template #default="{ row }">
              <div class="entity-info">
                <el-avatar
                  :size="24"
                  :style="{ backgroundColor: getEntityTypeColor(row.sourceEntity.type) }"
                >
                  {{ row.sourceEntity.name.charAt(0) }}
                </el-avatar>
                <span class="entity-name">{{ row.sourceEntity.name }}</span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="关系" width="80" align="center">
            <template #default="{ row }">
              <el-icon class="relation-arrow" :style="{ color: getTypeColor(row.type) }">
                <Right />
              </el-icon>
            </template>
          </el-table-column>
          
          <el-table-column label="目标实体" min-width="150">
            <template #default="{ row }">
              <div class="entity-info">
                <el-avatar
                  :size="24"
                  :style="{ backgroundColor: getEntityTypeColor(row.targetEntity.type) }"
                >
                  {{ row.targetEntity.name.charAt(0) }}
                </el-avatar>
                <span class="entity-name">{{ row.targetEntity.name }}</span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          
          <el-table-column prop="weight" label="权重" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="getWeightType(row.weight)">
                {{ row.weight || 1 }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="graphName" label="所属图谱" width="120" show-overflow-tooltip />
          
          <el-table-column prop="createdAt" label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.createdAt) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button-group>
                <el-button size="small" @click="viewRelation(row)">
                  <el-icon><View /></el-icon>
                </el-button>
                <el-button size="small" @click="editRelation(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" @click="viewInGraph(row)">
                  <el-icon><Share /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  @click="deleteRelation(row)"
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
            v-for="relation in relationsList"
            :key="relation.id"
            class="relation-card"
            :class="{ selected: selectedRelations.includes(relation.id) }"
            @click="toggleSelection(relation)"
          >
            <el-card shadow="hover">
              <div class="card-header">
                <div class="relation-icon">
                  <el-icon :style="{ color: getTypeColor(relation.type) }">
                    <component :is="getTypeIcon(relation.type)" />
                  </el-icon>
                </div>
                <div class="relation-info">
                  <h3 class="relation-name">{{ relation.name }}</h3>
                  <el-tag
                    :type="getTypeTagType(relation.type)"
                    size="small"
                  >
                    {{ getTypeLabel(relation.type) }}
                  </el-tag>
                </div>
                <div class="card-actions">
                  <el-checkbox
                    :model-value="selectedRelations.includes(relation.id)"
                    @change="toggleSelection(relation)"
                    @click.stop
                  />
                </div>
              </div>
              
              <div class="card-content">
                <div class="relation-flow">
                  <div class="entity source">
                    <el-avatar
                      :size="32"
                      :style="{ backgroundColor: getEntityTypeColor(relation.sourceEntity.type) }"
                    >
                      {{ relation.sourceEntity.name.charAt(0) }}
                    </el-avatar>
                    <span class="entity-name">{{ relation.sourceEntity.name }}</span>
                  </div>
                  
                  <div class="relation-arrow">
                    <el-icon :style="{ color: getTypeColor(relation.type) }">
                      <Right />
                    </el-icon>
                    <span class="relation-label">{{ relation.name }}</span>
                  </div>
                  
                  <div class="entity target">
                    <el-avatar
                      :size="32"
                      :style="{ backgroundColor: getEntityTypeColor(relation.targetEntity.type) }"
                    >
                      {{ relation.targetEntity.name.charAt(0) }}
                    </el-avatar>
                    <span class="entity-name">{{ relation.targetEntity.name }}</span>
                  </div>
                </div>
                
                <p class="description">{{ relation.description || '暂无描述' }}</p>
                
                <div class="stats">
                  <div class="stat-item">
                    <span class="label">权重：</span>
                    <el-tag size="small" :type="getWeightType(relation.weight)">
                      {{ relation.weight || 1 }}
                    </el-tag>
                  </div>
                  <div class="stat-item">
                    <span class="label">图谱：</span>
                    <span class="value">{{ relation.graphName }}</span>
                  </div>
                </div>
                
                <div class="properties" v-if="relation.properties">
                  <div class="properties-title">属性：</div>
                  <div class="properties-list">
                    <el-tag
                      v-for="(value, key) in getMainProperties(relation.properties)"
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
                  <span>{{ formatDate(relation.createdAt) }}</span>
                </div>
                <div class="actions">
                  <el-button size="small" @click.stop="viewRelation(relation)">
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button size="small" @click.stop="editRelation(relation)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button size="small" @click.stop="viewInGraph(relation)">
                    <el-icon><Share /></el-icon>
                  </el-button>
                  <el-button
                    size="small"
                    type="danger"
                    @click.stop="deleteRelation(relation)"
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
            <!-- 这里将集成关系图谱可视化组件 -->
            <div class="graph-placeholder">
              <el-icon><Share /></el-icon>
              <p>关系图谱可视化视图</p>
              <p class="sub-text">显示实体关系网络图</p>
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
    
    <!-- 创建/编辑关系对话框 -->
    <el-dialog
      v-model="relationDialogVisible"
      :title="isEdit ? '编辑关系' : '创建关系'"
      width="800px"
      :before-close="handleRelationDialogClose"
    >
      <el-form
        ref="relationFormRef"
        :model="relationForm"
        :rules="relationRules"
        label-width="100px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="关系名称" prop="name">
              <el-input v-model="relationForm.name" placeholder="请输入关系名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关系类型" prop="type">
              <el-select
                v-model="relationForm.type"
                placeholder="请选择关系类型"
                filterable
                allow-create
              >
                <el-option
                  v-for="type in relationTypes"
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
            <el-form-item label="源实体" prop="sourceEntityId">
              <el-select
                v-model="relationForm.sourceEntityId"
                placeholder="请选择源实体"
                filterable
                remote
                :remote-method="searchEntities"
                :loading="entitySearchLoading"
              >
                <el-option
                  v-for="entity in entityOptions"
                  :key="entity.id"
                  :label="`${entity.name} (${entity.type})`"
                  :value="entity.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标实体" prop="targetEntityId">
              <el-select
                v-model="relationForm.targetEntityId"
                placeholder="请选择目标实体"
                filterable
                remote
                :remote-method="searchEntities"
                :loading="entitySearchLoading"
              >
                <el-option
                  v-for="entity in entityOptions"
                  :key="entity.id"
                  :label="`${entity.name} (${entity.type})`"
                  :value="entity.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所属图谱" prop="graphId">
              <el-select
                v-model="relationForm.graphId"
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
            <el-form-item label="权重">
              <el-input-number
                v-model="relationForm.weight"
                :min="0"
                :max="10"
                :step="0.1"
                placeholder="关系权重"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="方向性">
              <el-switch
                v-model="relationForm.directed"
                active-text="有向"
                inactive-text="无向"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-switch
                v-model="relationForm.active"
                active-text="启用"
                inactive-text="禁用"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="描述">
          <el-input
            v-model="relationForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入关系描述"
          />
        </el-form-item>
        
        <el-form-item label="属性">
          <div class="properties-editor">
            <div
              v-for="(property, index) in relationForm.properties"
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
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="relationDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleRelationSubmit" :loading="submitting">
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 关系详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="关系详情"
      width="900px"
    >
      <div v-if="currentRelation" class="relation-detail">
        <div class="detail-header">
          <div class="relation-flow-detail">
            <div class="entity source">
              <el-avatar
                :size="48"
                :style="{ backgroundColor: getEntityTypeColor(currentRelation.sourceEntity.type) }"
              >
                {{ currentRelation.sourceEntity.name.charAt(0) }}
              </el-avatar>
              <div class="entity-info">
                <div class="name">{{ currentRelation.sourceEntity.name }}</div>
                <div class="type">{{ currentRelation.sourceEntity.type }}</div>
              </div>
            </div>
            
            <div class="relation-info">
              <el-icon :style="{ color: getTypeColor(currentRelation.type) }">
                <Right />
              </el-icon>
              <div class="relation-name">{{ currentRelation.name }}</div>
              <el-tag :type="getTypeTagType(currentRelation.type)">
                {{ getTypeLabel(currentRelation.type) }}
              </el-tag>
            </div>
            
            <div class="entity target">
              <el-avatar
                :size="48"
                :style="{ backgroundColor: getEntityTypeColor(currentRelation.targetEntity.type) }"
              >
                {{ currentRelation.targetEntity.name.charAt(0) }}
              </el-avatar>
              <div class="entity-info">
                <div class="name">{{ currentRelation.targetEntity.name }}</div>
                <div class="type">{{ currentRelation.targetEntity.type }}</div>
              </div>
            </div>
          </div>
        </div>
        
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <div class="basic-info">
              <div class="info-item">
                <span class="label">描述：</span>
                <span class="value">{{ currentRelation.description || '暂无描述' }}</span>
              </div>
              <div class="info-item">
                <span class="label">权重：</span>
                <span class="value">{{ currentRelation.weight || 1 }}</span>
              </div>
              <div class="info-item">
                <span class="label">方向性：</span>
                <span class="value">{{ currentRelation.directed ? '有向' : '无向' }}</span>
              </div>
              <div class="info-item">
                <span class="label">创建时间：</span>
                <span class="value">{{ formatDate(currentRelation.createdAt) }}</span>
              </div>
              <div class="info-item">
                <span class="label">更新时间：</span>
                <span class="value">{{ formatDate(currentRelation.updatedAt) }}</span>
              </div>
              <div class="info-item">
                <span class="label">创建者：</span>
                <span class="value">{{ currentRelation.createdBy || '系统' }}</span>
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="属性" name="properties">
            <div class="properties-detail">
              <el-table
                :data="formatProperties(currentRelation.properties)"
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
          
          <el-tab-pane label="路径分析" name="path">
            <div class="path-analysis">
              <!-- 路径分析功能将在这里实现 -->
              <p>路径分析功能开发中...</p>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Share,
  Plus,
  Upload,
  Search,
  Refresh,
  Delete,
  Download,
  Edit,
  List,
  Grid,
  View,
  Clock,
  Right,
  Connection,
  Link,
  Promotion
} from '@element-plus/icons-vue'
import { format } from 'date-fns'

const router = useRouter()
const route = useRoute()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const entitySearchLoading = ref(false)
const viewMode = ref('table') // table, card, graph
const selectAll = ref(false)
const selectedRelations = ref<string[]>([])
const relationDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const isEdit = ref(false)
const currentRelation = ref(null)
const activeTab = ref('basic')
const relationFormRef = ref()

// 搜索表单
const searchForm = reactive({
  keyword: '',
  graphId: '',
  type: '',
  sourceEntity: '',
  targetEntity: ''
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 关系表单
const relationForm = reactive({
  id: '',
  name: '',
  type: '',
  sourceEntityId: '',
  targetEntityId: '',
  graphId: '',
  description: '',
  weight: 1,
  directed: true,
  properties: [],
  active: true
})

// 表单验证规则
const relationRules = {
  name: [
    { required: true, message: '请输入关系名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择关系类型', trigger: 'change' }
  ],
  sourceEntityId: [
    { required: true, message: '请选择源实体', trigger: 'change' }
  ],
  targetEntityId: [
    { required: true, message: '请选择目标实体', trigger: 'change' }
  ],
  graphId: [
    { required: true, message: '请选择知识图谱', trigger: 'change' }
  ]
}

// 模拟数据
const relationsList = ref([
  {
    id: '1',
    name: '工作于',
    type: 'works_at',
    description: '员工在某个部门工作',
    sourceEntity: {
      id: '1',
      name: '张三',
      type: 'person'
    },
    targetEntity: {
      id: '2',
      name: '技术部',
      type: 'organization'
    },
    weight: 1.0,
    directed: true,
    properties: {
      startDate: '2023-01-01',
      position: '高级工程师',
      salary: '15000'
    },
    graphId: 'graph1',
    graphName: '员工关系图谱',
    createdAt: '2024-01-15T10:30:00Z',
    updatedAt: '2024-01-20T14:20:00Z',
    createdBy: 'admin'
  },
  {
    id: '2',
    name: '使用',
    type: 'uses',
    description: '项目使用某种技术',
    sourceEntity: {
      id: '3',
      name: 'ERAG项目',
      type: 'product'
    },
    targetEntity: {
      id: '4',
      name: 'Vue.js',
      type: 'technology'
    },
    weight: 0.8,
    directed: true,
    properties: {
      version: '3.4.0',
      usage: 'frontend'
    },
    graphId: 'graph2',
    graphName: '技术栈图谱',
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

const relationTypes = ref([
  { label: '工作于', value: 'works_at' },
  { label: '属于', value: 'belongs_to' },
  { label: '使用', value: 'uses' },
  { label: '依赖', value: 'depends_on' },
  { label: '包含', value: 'contains' },
  { label: '关联', value: 'related_to' },
  { label: '继承', value: 'inherits' },
  { label: '实现', value: 'implements' }
])

const entityOptions = ref([
  { id: '1', name: '张三', type: 'person' },
  { id: '2', name: '技术部', type: 'organization' },
  { id: '3', name: 'ERAG项目', type: 'product' },
  { id: '4', name: 'Vue.js', type: 'technology' }
])

// 计算属性
const isIndeterminate = computed(() => {
  const selected = selectedRelations.value.length
  const total = relationsList.value.length
  return selected > 0 && selected < total
})

// 方法
const formatDate = (dateString: string) => {
  return format(new Date(dateString), 'yyyy-MM-dd HH:mm')
}

const getTypeColor = (type: string) => {
  const colors = {
    works_at: '#409eff',
    belongs_to: '#67c23a',
    uses: '#e6a23c',
    depends_on: '#f56c6c',
    contains: '#909399',
    related_to: '#c71585',
    inherits: '#20b2aa',
    implements: '#ff7f50'
  }
  return colors[type] || '#909399'
}

const getTypeTagType = (type: string) => {
  const types = {
    works_at: 'primary',
    belongs_to: 'success',
    uses: 'warning',
    depends_on: 'danger',
    contains: 'info',
    related_to: 'primary',
    inherits: 'success',
    implements: 'warning'
  }
  return types[type] || 'info'
}

const getTypeLabel = (type: string) => {
  const typeObj = relationTypes.value.find(t => t.value === type)
  return typeObj ? typeObj.label : type
}

const getTypeIcon = (type: string) => {
  const icons = {
    works_at: 'Connection',
    belongs_to: 'Link',
    uses: 'Promotion',
    depends_on: 'Share',
    contains: 'Grid',
    related_to: 'Connection',
    inherits: 'Promotion',
    implements: 'Link'
  }
  return icons[type] || 'Connection'
}

const getEntityTypeColor = (type: string) => {
  const colors = {
    person: '#409eff',
    organization: '#67c23a',
    technology: '#e6a23c',
    product: '#f56c6c',
    concept: '#909399'
  }
  return colors[type] || '#909399'
}

const getWeightType = (weight: number) => {
  if (weight >= 0.8) return 'success'
  if (weight >= 0.5) return 'warning'
  return 'danger'
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
  loadRelations()
}

const handleReset = () => {
  Object.assign(searchForm, {
    keyword: '',
    graphId: '',
    type: '',
    sourceEntity: '',
    targetEntity: ''
  })
  handleSearch()
}

// 实体搜索
const searchEntities = async (query: string) => {
  if (!query) return
  
  entitySearchLoading.value = true
  try {
    // 这里调用搜索实体的API
    await new Promise(resolve => setTimeout(resolve, 300))
    // 模拟搜索结果
  } catch (error) {
    ElMessage.error('搜索实体失败')
  } finally {
    entitySearchLoading.value = false
  }
}

// 选择操作
const handleSelectAll = (checked: boolean) => {
  if (checked) {
    selectedRelations.value = relationsList.value.map(item => item.id)
  } else {
    selectedRelations.value = []
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedRelations.value = selection.map(item => item.id)
  selectAll.value = selection.length === relationsList.value.length
}

const toggleSelection = (relation: any) => {
  const index = selectedRelations.value.indexOf(relation.id)
  if (index > -1) {
    selectedRelations.value.splice(index, 1)
  } else {
    selectedRelations.value.push(relation.id)
  }
  selectAll.value = selectedRelations.value.length === relationsList.value.length
}

// 批量操作
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRelations.value.length} 个关系吗？`,
      '批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里调用删除API
    ElMessage.success('删除成功')
    selectedRelations.value = []
    loadRelations()
    
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
  loadRelations()
}

// 分页
const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  loadRelations()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadRelations()
}

// 关系操作
const showCreateDialog = () => {
  isEdit.value = false
  resetRelationForm()
  relationDialogVisible.value = true
}

const showImportDialog = () => {
  ElMessage.info('批量导入功能开发中...')
}

const viewRelation = (relation: any) => {
  currentRelation.value = relation
  activeTab.value = 'basic'
  detailDialogVisible.value = true
}

const editRelation = (relation: any) => {
  isEdit.value = true
  Object.assign(relationForm, {
    ...relation,
    sourceEntityId: relation.sourceEntity.id,
    targetEntityId: relation.targetEntity.id,
    properties: Object.entries(relation.properties || {}).map(([key, value]) => ({
      key,
      value: String(value),
      type: typeof value === 'number' ? 'number' : 
            typeof value === 'boolean' ? 'boolean' :
            value instanceof Date ? 'date' : 'string'
    }))
  })
  relationDialogVisible.value = true
}

const deleteRelation = async (relation: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除关系 "${relation.name}" 吗？`,
      '删除关系',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里调用删除API
    ElMessage.success('删除成功')
    loadRelations()
    
  } catch (error) {
    // 用户取消
  }
}

const viewInGraph = (relation: any) => {
  router.push(`/knowledge/graphs/${relation.graphId}?highlight=${relation.id}`)
}

// 表单操作
const resetRelationForm = () => {
  Object.assign(relationForm, {
    id: '',
    name: '',
    type: '',
    sourceEntityId: '',
    targetEntityId: '',
    graphId: '',
    description: '',
    weight: 1,
    directed: true,
    properties: [],
    active: true
  })
  relationFormRef.value?.clearValidate()
}

const handleRelationDialogClose = () => {
  resetRelationForm()
  relationDialogVisible.value = false
}

const addProperty = () => {
  relationForm.properties.push({
    key: '',
    value: '',
    type: 'string'
  })
}

const removeProperty = (index: number) => {
  relationForm.properties.splice(index, 1)
}

const handleRelationSubmit = async () => {
  try {
    await relationFormRef.value.validate()
    
    if (relationForm.sourceEntityId === relationForm.targetEntityId) {
      ElMessage.warning('源实体和目标实体不能相同')
      return
    }
    
    submitting.value = true
    
    // 转换属性格式
    const properties = {}
    relationForm.properties.forEach(prop => {
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
      ...relationForm,
      properties
    }
    
    // 这里调用创建或更新API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    relationDialogVisible.value = false
    loadRelations()
    
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitting.value = false
  }
}

// 数据加载
const loadRelations = async () => {
  try {
    loading.value = true
    
    // 这里调用获取关系列表的API
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟分页数据
    pagination.total = 30
    
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 页面初始化
onMounted(() => {
  // 检查是否有实体ID参数（从实体页面跳转过来）
  const entityId = route.query.entityId as string
  if (entityId) {
    searchForm.sourceEntity = entityId
    searchForm.targetEntity = entityId
  }
  
  loadRelations()
})
</script>

<style lang="scss" scoped>
.relations-page {
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
        min-width: 180px;
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

.relations-content {
  margin-bottom: 20px;
}

// 表格视图样式
.relation-name {
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

.entity-info {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .entity-name {
    font-size: 14px;
    color: #2c3e50;
  }
}

.relation-arrow {
  font-size: 16px;
}

// 卡片视图样式
.card-view {
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
      gap: 20px;
    }
    
    .relation-card {
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
    }
  }
  
  @media (max-width: 768px) {
    .card-view {
      .cards-grid {
        grid-template-columns: 1fr;
      }
    }
  }
}
</style>