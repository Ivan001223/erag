<template>
  <div class="documents-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Document /></el-icon>
            文档管理
          </h1>
          <p class="page-description">
            上传、处理和管理文档，支持OCR识别和知识抽取
          </p>
        </div>
        <div class="header-right">
          <el-button type="primary" @click="showUploadDialog">
            <el-icon><Upload /></el-icon>
            上传文档
          </el-button>
          <el-button @click="showBatchUploadDialog">
            <el-icon><FolderOpened /></el-icon>
            批量上传
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
                placeholder="搜索文档名称、内容或标签"
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
                placeholder="文档类型"
                clearable
                filterable
              >
                <el-option
                  v-for="type in documentTypes"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
            </div>
            
            <div class="search-item">
              <el-select
                v-model="searchForm.status"
                placeholder="处理状态"
                clearable
              >
                <el-option label="全部" value="" />
                <el-option label="待处理" value="pending" />
                <el-option label="处理中" value="processing" />
                <el-option label="已完成" value="completed" />
                <el-option label="失败" value="failed" />
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
        <span class="selected-info" v-if="selectedDocuments.length > 0">
          已选择 {{ selectedDocuments.length }} 个文档
        </span>
      </div>
      
      <div class="toolbar-center">
        <el-button-group>
          <el-button
            :disabled="selectedDocuments.length === 0"
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
          <el-button
            :disabled="selectedDocuments.length === 0"
            @click="handleBatchReprocess"
          >
            <el-icon><Refresh /></el-icon>
            重新处理
          </el-button>
          <el-button
            :disabled="selectedDocuments.length === 0"
            @click="handleBatchDownload"
          >
            <el-icon><Download /></el-icon>
            批量下载
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
        </el-button-group>
      </div>
    </div>
    
    <!-- 文档列表 -->
    <div class="documents-content">
      <!-- 表格视图 -->
      <el-card v-if="viewMode === 'table'" shadow="never">
        <el-table
          v-loading="loading"
          :data="documentsList"
          @selection-change="handleSelectionChange"
          stripe
          style="width: 100%"
        >
          <el-table-column type="selection" width="55" />
          
          <el-table-column prop="name" label="文档名称" min-width="200">
            <template #default="{ row }">
              <div class="document-name">
                <el-icon class="file-icon" :style="{ color: getFileTypeColor(row.type) }">
                  <component :is="getFileTypeIcon(row.type)" />
                </el-icon>
                <div class="name-info">
                  <div class="name">{{ row.name }}</div>
                  <div class="size">{{ formatFileSize(row.size) }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="getTypeTagType(row.type)">
                {{ getTypeLabel(row.type) }}
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
          
          <el-table-column prop="progress" label="进度" width="120">
            <template #default="{ row }">
              <el-progress
                v-if="row.status === 'processing'"
                :percentage="row.progress || 0"
                :stroke-width="6"
                :show-text="false"
              />
              <span v-else-if="row.status === 'completed'" class="progress-text">
                100%
              </span>
              <span v-else class="progress-text">-</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="extractedEntities" label="实体" width="80">
            <template #default="{ row }">
              <el-tag size="small" type="info">
                {{ row.extractedEntities || 0 }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="extractedRelations" label="关系" width="80">
            <template #default="{ row }">
              <el-tag size="small" type="warning">
                {{ row.extractedRelations || 0 }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="uploadedAt" label="上传时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.uploadedAt) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button-group>
                <el-button size="small" @click="viewDocument(row)">
                  <el-icon><View /></el-icon>
                </el-button>
                <el-button size="small" @click="downloadDocument(row)">
                  <el-icon><Download /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  :disabled="row.status === 'processing'"
                  @click="reprocessDocument(row)"
                >
                  <el-icon><Refresh /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  @click="deleteDocument(row)"
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
            v-for="document in documentsList"
            :key="document.id"
            class="document-card"
            :class="{ selected: selectedDocuments.includes(document.id) }"
            @click="toggleSelection(document)"
          >
            <el-card shadow="hover">
              <div class="card-header">
                <div class="file-preview">
                  <el-icon class="file-icon" :style="{ color: getFileTypeColor(document.type) }">
                    <component :is="getFileTypeIcon(document.type)" />
                  </el-icon>
                </div>
                <div class="document-info">
                  <h3 class="document-name">{{ document.name }}</h3>
                  <div class="document-meta">
                    <el-tag size="small" :type="getTypeTagType(document.type)">
                      {{ getTypeLabel(document.type) }}
                    </el-tag>
                    <span class="file-size">{{ formatFileSize(document.size) }}</span>
                  </div>
                </div>
                <div class="card-actions">
                  <el-checkbox
                    :model-value="selectedDocuments.includes(document.id)"
                    @change="toggleSelection(document)"
                    @click.stop
                  />
                </div>
              </div>
              
              <div class="card-content">
                <div class="status-info">
                  <el-tag
                    :type="getStatusTagType(document.status)"
                    :icon="getStatusIcon(document.status)"
                  >
                    {{ getStatusLabel(document.status) }}
                  </el-tag>
                  <el-progress
                    v-if="document.status === 'processing'"
                    :percentage="document.progress || 0"
                    :stroke-width="4"
                    class="progress-bar"
                  />
                </div>
                
                <div class="extraction-stats">
                  <div class="stat-item">
                    <span class="stat-label">实体:</span>
                    <span class="stat-value">{{ document.extractedEntities || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">关系:</span>
                    <span class="stat-value">{{ document.extractedRelations || 0 }}</span>
                  </div>
                </div>
                
                <div class="upload-time">
                  {{ formatDate(document.uploadedAt) }}
                </div>
              </div>
              
              <div class="card-footer">
                <el-button-group>
                  <el-button size="small" @click.stop="viewDocument(document)">
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button size="small" @click.stop="downloadDocument(document)">
                    <el-icon><Download /></el-icon>
                  </el-button>
                  <el-button
                    size="small"
                    :disabled="document.status === 'processing'"
                    @click.stop="reprocessDocument(document)"
                  >
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                  <el-button
                    size="small"
                    type="danger"
                    @click.stop="deleteDocument(document)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-button-group>
              </div>
            </el-card>
          </div>
        </div>
      </div>
      
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
    </div>
    
    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文档"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="upload-section">
        <el-upload
          ref="uploadRef"
          class="upload-dragger"
          drag
          :action="uploadUrl"
          :headers="uploadHeaders"
          :data="uploadData"
          :file-list="fileList"
          :before-upload="beforeUpload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :on-progress="onUploadProgress"
          :on-remove="onFileRemove"
          multiple
          :accept="acceptedFileTypes"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 PDF、Word、Excel、PowerPoint、图片等格式，单个文件不超过 100MB
            </div>
          </template>
        </el-upload>
        
        <div class="upload-options">
          <el-form :model="uploadForm" label-width="100px">
            <el-form-item label="知识图谱">
              <el-select
                v-model="uploadForm.graphId"
                placeholder="选择目标知识图谱"
                style="width: 100%"
              >
                <el-option
                  v-for="graph in graphList"
                  :key="graph.id"
                  :label="graph.name"
                  :value="graph.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="处理选项">
              <el-checkbox-group v-model="uploadForm.options">
                <el-checkbox label="ocr">OCR识别</el-checkbox>
                <el-checkbox label="extract_entities">实体抽取</el-checkbox>
                <el-checkbox label="extract_relations">关系抽取</el-checkbox>
                <el-checkbox label="auto_link">自动关联</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item label="标签">
              <el-tag
                v-for="tag in uploadForm.tags"
                :key="tag"
                closable
                @close="removeTag(tag)"
                style="margin-right: 8px; margin-bottom: 8px;"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-if="tagInputVisible"
                ref="tagInputRef"
                v-model="tagInputValue"
                class="tag-input"
                size="small"
                @keyup.enter="addTag"
                @blur="addTag"
              />
              <el-button
                v-else
                class="button-new-tag"
                size="small"
                @click="showTagInput"
              >
                + 添加标签
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="startUpload">开始上传</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 文档详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="currentDocument?.name"
      width="80%"
      :close-on-click-modal="false"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="基本信息" name="basic">
          <div class="document-detail">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="文档名称">
                {{ currentDocument?.name }}
              </el-descriptions-item>
              <el-descriptions-item label="文件类型">
                <el-tag :type="getTypeTagType(currentDocument?.type)">
                  {{ getTypeLabel(currentDocument?.type) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="文件大小">
                {{ formatFileSize(currentDocument?.size) }}
              </el-descriptions-item>
              <el-descriptions-item label="处理状态">
                <el-tag :type="getStatusTagType(currentDocument?.status)">
                  {{ getStatusLabel(currentDocument?.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="上传时间">
                {{ formatDate(currentDocument?.uploadedAt) }}
              </el-descriptions-item>
              <el-descriptions-item label="处理时间">
                {{ formatDate(currentDocument?.processedAt) }}
              </el-descriptions-item>
              <el-descriptions-item label="抽取实体">
                {{ currentDocument?.extractedEntities || 0 }} 个
              </el-descriptions-item>
              <el-descriptions-item label="抽取关系">
                {{ currentDocument?.extractedRelations || 0 }} 个
              </el-descriptions-item>
            </el-descriptions>
            
            <div v-if="currentDocument?.tags?.length" class="document-tags">
              <h4>标签</h4>
              <el-tag
                v-for="tag in currentDocument.tags"
                :key="tag"
                style="margin-right: 8px; margin-bottom: 8px;"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="OCR结果" name="ocr">
          <div class="ocr-content">
            <el-input
              v-model="currentDocument?.ocrText"
              type="textarea"
              :rows="20"
              readonly
              placeholder="OCR识别结果将显示在这里"
            />
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="抽取实体" name="entities">
          <div class="extracted-entities">
            <el-table
              :data="currentDocument?.entities || []"
              stripe
              style="width: 100%"
            >
              <el-table-column prop="name" label="实体名称" />
              <el-table-column prop="type" label="类型">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="confidence" label="置信度">
                <template #default="{ row }">
                  <el-progress
                    :percentage="Math.round(row.confidence * 100)"
                    :stroke-width="6"
                    :show-text="false"
                  />
                  <span class="confidence-text">{{ Math.round(row.confidence * 100) }}%</span>
                </template>
              </el-table-column>
              <el-table-column prop="position" label="位置" />
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="抽取关系" name="relations">
          <div class="extracted-relations">
            <el-table
              :data="currentDocument?.relations || []"
              stripe
              style="width: 100%"
            >
              <el-table-column prop="source" label="源实体" />
              <el-table-column prop="relation" label="关系类型" />
              <el-table-column prop="target" label="目标实体" />
              <el-table-column prop="confidence" label="置信度">
                <template #default="{ row }">
                  <el-progress
                    :percentage="Math.round(row.confidence * 100)"
                    :stroke-width="6"
                    :show-text="false"
                  />
                  <span class="confidence-text">{{ Math.round(row.confidence * 100) }}%</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  Upload,
  FolderOpened,
  Search,
  Refresh,
  Delete,
  Download,
  List,
  Grid,
  View,
  Edit,
  Plus,
  UploadFilled,
  DocumentCopy,
  Picture,
  VideoPlay,
  Files
} from '@element-plus/icons-vue'

// 响应式数据
const loading = ref(false)
const viewMode = ref('table')
const selectAll = ref(false)
const selectedDocuments = ref<string[]>([])
const uploadDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const currentDocument = ref<any>(null)
const activeTab = ref('basic')
const tagInputVisible = ref(false)
const tagInputValue = ref('')
const tagInputRef = ref()
const uploadRef = ref()
const fileList = ref([])

// 搜索表单
const searchForm = reactive({
  keyword: '',
  type: '',
  status: '',
  dateRange: []
})

// 上传表单
const uploadForm = reactive({
  graphId: '',
  options: ['ocr', 'extract_entities', 'extract_relations'],
  tags: []
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 文档列表
const documentsList = ref([
  {
    id: '1',
    name: '企业知识管理手册.pdf',
    type: 'pdf',
    size: 2048576,
    status: 'completed',
    progress: 100,
    extractedEntities: 45,
    extractedRelations: 23,
    uploadedAt: '2024-01-15 10:30:00',
    processedAt: '2024-01-15 10:35:00',
    tags: ['管理', '知识库'],
    ocrText: '这是OCR识别的文本内容...',
    entities: [
      { name: '知识管理', type: 'concept', confidence: 0.95, position: '第1页' },
      { name: '企业', type: 'organization', confidence: 0.88, position: '第1页' }
    ],
    relations: [
      { source: '企业', relation: '实施', target: '知识管理', confidence: 0.92 }
    ]
  },
  {
    id: '2',
    name: '技术架构图.png',
    type: 'image',
    size: 1024000,
    status: 'processing',
    progress: 65,
    extractedEntities: 0,
    extractedRelations: 0,
    uploadedAt: '2024-01-15 11:00:00',
    tags: ['技术', '架构']
  },
  {
    id: '3',
    name: '产品需求文档.docx',
    type: 'word',
    size: 512000,
    status: 'failed',
    progress: 0,
    extractedEntities: 0,
    extractedRelations: 0,
    uploadedAt: '2024-01-15 09:45:00',
    tags: ['产品', '需求']
  }
])

// 知识图谱列表
const graphList = ref([
  { id: '1', name: '企业知识图谱' },
  { id: '2', name: '技术知识图谱' },
  { id: '3', name: '产品知识图谱' }
])

// 文档类型
const documentTypes = ref([
  { label: 'PDF文档', value: 'pdf' },
  { label: 'Word文档', value: 'word' },
  { label: 'Excel表格', value: 'excel' },
  { label: 'PowerPoint', value: 'ppt' },
  { label: '图片', value: 'image' },
  { label: '文本文件', value: 'text' }
])

// 计算属性
const isIndeterminate = computed(() => {
  const selected = selectedDocuments.value.length
  const total = documentsList.value.length
  return selected > 0 && selected < total
})

const uploadUrl = computed(() => '/api/v1/documents/upload')
const uploadHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token')}`
}))
const uploadData = computed(() => ({
  graphId: uploadForm.graphId,
  options: uploadForm.options.join(','),
  tags: uploadForm.tags.join(',')
}))
const acceptedFileTypes = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif'

// 方法
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getFileTypeIcon = (type: string) => {
  const icons = {
    pdf: DocumentCopy,
    word: DocumentCopy,
    excel: Files,
    ppt: Files,
    image: Picture,
    video: VideoPlay,
    text: Document
  }
  return icons[type] || Document
}

const getFileTypeColor = (type: string) => {
  const colors = {
    pdf: '#f56565',
    word: '#4299e1',
    excel: '#48bb78',
    ppt: '#ed8936',
    image: '#9f7aea',
    video: '#38b2ac',
    text: '#718096'
  }
  return colors[type] || '#718096'
}

const getTypeTagType = (type: string) => {
  const types = {
    pdf: 'danger',
    word: 'primary',
    excel: 'success',
    ppt: 'warning',
    image: 'info',
    video: 'info',
    text: 'info'
  }
  return types[type] || 'info'
}

const getTypeLabel = (type: string) => {
  const typeObj = documentTypes.value.find(t => t.value === type)
  return typeObj ? typeObj.label : type.toUpperCase()
}

const getStatusTagType = (status: string) => {
  const types = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const labels = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '处理失败'
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
  loadDocuments()
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

// 选择操作
const handleSelectAll = (checked: boolean) => {
  if (checked) {
    selectedDocuments.value = documentsList.value.map(item => item.id)
  } else {
    selectedDocuments.value = []
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedDocuments.value = selection.map(item => item.id)
  selectAll.value = selection.length === documentsList.value.length
}

const toggleSelection = (document: any) => {
  const index = selectedDocuments.value.indexOf(document.id)
  if (index > -1) {
    selectedDocuments.value.splice(index, 1)
  } else {
    selectedDocuments.value.push(document.id)
  }
  selectAll.value = selectedDocuments.value.length === documentsList.value.length
}

// 批量操作
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedDocuments.value.length} 个文档吗？`,
      '批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('删除成功')
    selectedDocuments.value = []
    loadDocuments()
    
  } catch (error) {
    // 用户取消
  }
}

const handleBatchReprocess = () => {
  ElMessage.info('重新处理功能开发中...')
}

const handleBatchDownload = () => {
  ElMessage.info('批量下载功能开发中...')
}

// 刷新
const handleRefresh = () => {
  loadDocuments()
}

// 分页
const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  loadDocuments()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadDocuments()
}

// 文档操作
const showUploadDialog = () => {
  uploadDialogVisible.value = true
  fileList.value = []
}

const showBatchUploadDialog = () => {
  ElMessage.info('批量上传功能开发中...')
}

const viewDocument = (document: any) => {
  currentDocument.value = document
  activeTab.value = 'basic'
  detailDialogVisible.value = true
}

const downloadDocument = (document: any) => {
  ElMessage.info('下载功能开发中...')
}

const reprocessDocument = async (document: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要重新处理文档 "${document.name}" 吗？`,
      '重新处理',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('已提交重新处理请求')
    loadDocuments()
    
  } catch (error) {
    // 用户取消
  }
}

const deleteDocument = async (document: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档 "${document.name}" 吗？`,
      '删除文档',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('删除成功')
    loadDocuments()
    
  } catch (error) {
    // 用户取消
  }
}

// 上传相关
const beforeUpload = (file: any) => {
  const isValidType = acceptedFileTypes.includes(`.${file.name.split('.').pop()?.toLowerCase()}`)
  const isValidSize = file.size / 1024 / 1024 < 100
  
  if (!isValidType) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  if (!isValidSize) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }
  return true
}

const onUploadSuccess = (response: any, file: any) => {
  ElMessage.success(`${file.name} 上传成功`)
  loadDocuments()
}

const onUploadError = (error: any, file: any) => {
  ElMessage.error(`${file.name} 上传失败`)
}

const onUploadProgress = (event: any, file: any) => {
  // 处理上传进度
}

const onFileRemove = (file: any) => {
  // 处理文件移除
}

const startUpload = () => {
  if (!uploadForm.graphId) {
    ElMessage.warning('请选择目标知识图谱')
    return
  }
  uploadRef.value?.submit()
}

// 标签管理
const showTagInput = () => {
  tagInputVisible.value = true
  nextTick(() => {
    tagInputRef.value?.focus()
  })
}

const addTag = () => {
  const tag = tagInputValue.value.trim()
  if (tag && !uploadForm.tags.includes(tag)) {
    uploadForm.tags.push(tag)
  }
  tagInputVisible.value = false
  tagInputValue.value = ''
}

const removeTag = (tag: string) => {
  const index = uploadForm.tags.indexOf(tag)
  if (index > -1) {
    uploadForm.tags.splice(index, 1)
  }
}

// 加载数据
const loadDocuments = async () => {
  loading.value = true
  try {
    // 这里调用API加载文档列表
    // const response = await documentsApi.getList(searchForm, pagination)
    // documentsList.value = response.data.items
    // pagination.total = response.data.total
    
    // 模拟加载延迟
    await new Promise(resolve => setTimeout(resolve, 500))
    
  } catch (error) {
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.documents-page {
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

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 16px 24px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.selected-info {
  color: #6b7280;
  font-size: 14px;
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

.documents-content {
  margin-bottom: 20px;
}

.document-name {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 24px;
}

.name-info {
  flex: 1;
}

.name {
  font-weight: 500;
  color: #1f2937;
}

.size {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.progress-text {
  font-size: 12px;
  color: #6b7280;
}

.card-view {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.document-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.document-card.selected {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.file-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: #f3f4f6;
}

.document-info {
  flex: 1;
}

.document-name {
  font-weight: 500;
  color: #1f2937;
  margin: 0 0 8px 0;
  font-size: 16px;
}

.document-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-size {
  font-size: 12px;
  color: #6b7280;
}

.card-actions {
  display: flex;
  align-items: center;
}

.card-content {
  margin-bottom: 16px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.progress-bar {
  flex: 1;
}

.extraction-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
}

.stat-label {
  color: #6b7280;
}

.stat-value {
  font-weight: 500;
  color: #1f2937;
}

.upload-time {
  font-size: 12px;
  color: #6b7280;
}

.card-footer {
  display: flex;
  justify-content: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-dragger {
  width: 100%;
}

.upload-options {
  background: #f9fafb;
  padding: 20px;
  border-radius: 8px;
}

.tag-input {
  width: 100px;
}

.button-new-tag {
  border-style: dashed;
}

.document-detail {
  padding: 20px;
}

.document-tags {
  margin-top: 20px;
}

.document-tags h4 {
  margin: 0 0 12px 0;
  color: #1f2937;
}

.ocr-content {
  padding: 20px;
}

.extracted-entities,
.extracted-relations {
  padding: 20px;
}

.confidence-text {
  margin-left: 8px;
  font-size: 12px;
  color: #6b7280;
}

@media (max-width: 768px) {
  .documents-page {
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
  
  .toolbar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .toolbar-left,
  .toolbar-center,
  .toolbar-right {
    justify-content: center;
  }
  
  .cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>