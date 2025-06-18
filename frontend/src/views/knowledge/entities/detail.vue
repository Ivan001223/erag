<template>
  <div class="entity-detail">
    <!-- 页面头部 -->
    <div class="detail-header">
      <div class="header-content">
        <div class="breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/knowledge' }">知识库</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ path: '/knowledge/entities' }">实体管理</el-breadcrumb-item>
            <el-breadcrumb-item>{{ entityData.name || '实体详情' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-actions">
          <el-button @click="$router.go(-1)">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <el-button type="primary" @click="editEntity">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
      </div>
    </div>

    <!-- 实体基本信息 -->
    <div class="entity-info-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>基本信息</h3>
            <div class="entity-status">
              <el-tag :type="getStatusType(entityData.status)">{{ entityData.status }}</el-tag>
            </div>
          </div>
        </template>
        
        <div class="entity-info">
          <div class="entity-avatar">
            <el-avatar :size="80" :src="entityData.avatar">
              <el-icon><User /></el-icon>
            </el-avatar>
          </div>
          
          <div class="entity-details">
            <div class="entity-name">
              <h2>{{ entityData.name }}</h2>
              <div class="entity-type">
                <el-tag size="small">{{ entityData.type }}</el-tag>
              </div>
            </div>
            
            <div class="entity-meta">
              <div class="meta-item">
                <span class="label">创建时间：</span>
                <span class="value">{{ formatDate(entityData.createTime) }}</span>
              </div>
              <div class="meta-item">
                <span class="label">更新时间：</span>
                <span class="value">{{ formatDate(entityData.updateTime) }}</span>
              </div>
              <div class="meta-item">
                <span class="label">创建者：</span>
                <span class="value">{{ entityData.creator }}</span>
              </div>
              <div class="meta-item">
                <span class="label">关联文档：</span>
                <span class="value">{{ entityData.documentCount }} 个</span>
              </div>
            </div>
            
            <div class="entity-description" v-if="entityData.description">
              <p>{{ entityData.description }}</p>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 属性信息 -->
    <div class="properties-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>属性信息</h3>
            <el-button size="small" @click="addProperty">
              <el-icon><Plus /></el-icon>
              添加属性
            </el-button>
          </div>
        </template>
        
        <div class="properties-list" v-loading="propertiesLoading">
          <div v-for="property in entityData.properties" :key="property.id" class="property-item">
            <div class="property-info">
              <div class="property-name">{{ property.name }}</div>
              <div class="property-type">{{ property.type }}</div>
            </div>
            <div class="property-value">
              <span v-if="property.type === 'text'">{{ property.value }}</span>
              <el-tag v-else-if="property.type === 'tag'" size="small">{{ property.value }}</el-tag>
              <span v-else-if="property.type === 'number'">{{ property.value }}</span>
              <span v-else-if="property.type === 'date'">{{ formatDate(property.value) }}</span>
              <el-link v-else-if="property.type === 'url'" :href="property.value" target="_blank">{{ property.value }}</el-link>
            </div>
            <div class="property-actions">
              <el-button size="small" text @click="editProperty(property)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click="deleteProperty(property.id)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          
          <div v-if="entityData.properties?.length === 0" class="empty-properties">
            <el-empty description="暂无属性信息" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 关系图谱 -->
    <div class="relations-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>关系图谱</h3>
            <div class="relation-controls">
              <el-button size="small" @click="refreshRelations">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button size="small" @click="addRelation">
                <el-icon><Plus /></el-icon>
                添加关系
              </el-button>
            </div>
          </div>
        </template>
        
        <div class="relations-content" v-loading="relationsLoading">
          <div class="relations-graph" ref="graphContainer">
            <!-- 这里应该集成图谱可视化组件，如 D3.js 或 ECharts -->
            <div class="graph-placeholder">
              <el-icon class="graph-icon"><Share /></el-icon>
              <p>关系图谱加载中...</p>
            </div>
          </div>
          
          <div class="relations-list">
            <h4>关系列表</h4>
            <div class="relation-items">
              <div v-for="relation in entityData.relations" :key="relation.id" class="relation-item">
                <div class="relation-info">
                  <div class="relation-source">{{ relation.source }}</div>
                  <div class="relation-type">
                    <el-icon><Right /></el-icon>
                    <span>{{ relation.type }}</span>
                    <el-icon><Right /></el-icon>
                  </div>
                  <div class="relation-target">{{ relation.target }}</div>
                </div>
                <div class="relation-actions">
                  <el-button size="small" text @click="viewRelatedEntity(relation.targetId)">
                    查看
                  </el-button>
                  <el-button size="small" text type="danger" @click="deleteRelation(relation.id)">
                    删除
                  </el-button>
                </div>
              </div>
            </div>
            
            <div v-if="entityData.relations?.length === 0" class="empty-relations">
              <el-empty description="暂无关系信息" />
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 关联文档 -->
    <div class="documents-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>关联文档</h3>
            <el-button size="small" @click="linkDocument">
              <el-icon><Link /></el-icon>
              关联文档
            </el-button>
          </div>
        </template>
        
        <div class="documents-list" v-loading="documentsLoading">
          <div v-for="document in entityData.documents" :key="document.id" class="document-item">
            <div class="document-info">
              <div class="document-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="document-details">
                <div class="document-name">{{ document.name }}</div>
                <div class="document-meta">
                  <span class="document-type">{{ document.type }}</span>
                  <span class="document-size">{{ formatFileSize(document.size) }}</span>
                  <span class="document-time">{{ formatDate(document.updateTime) }}</span>
                </div>
              </div>
            </div>
            
            <div class="document-relevance">
              <el-rate v-model="document.relevance" disabled show-score />
            </div>
            
            <div class="document-actions">
              <el-button size="small" text @click="viewDocument(document.id)">
                查看
              </el-button>
              <el-button size="small" text @click="downloadDocument(document.id)">
                下载
              </el-button>
              <el-button size="small" text type="danger" @click="unlinkDocument(document.id)">
                取消关联
              </el-button>
            </div>
          </div>
          
          <div v-if="entityData.documents?.length === 0" class="empty-documents">
            <el-empty description="暂无关联文档" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 活动历史 -->
    <div class="activity-section">
      <el-card>
        <template #header>
          <h3>活动历史</h3>
        </template>
        
        <div class="activity-timeline" v-loading="activityLoading">
          <el-timeline>
            <el-timeline-item
              v-for="activity in entityData.activities"
              :key="activity.id"
              :timestamp="formatDate(activity.time)"
              :type="getActivityType(activity.type)"
            >
              <div class="activity-content">
                <div class="activity-title">{{ activity.title }}</div>
                <div class="activity-description">{{ activity.description }}</div>
                <div class="activity-user">{{ activity.user }}</div>
              </div>
            </el-timeline-item>
          </el-timeline>
          
          <div v-if="entityData.activities?.length === 0" class="empty-activity">
            <el-empty description="暂无活动记录" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑实体" width="600px">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="100px">
        <el-form-item label="实体名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入实体名称" />
        </el-form-item>
        <el-form-item label="实体类型" prop="type">
          <el-select v-model="editForm.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="人物" value="person" />
            <el-option label="组织" value="organization" />
            <el-option label="地点" value="location" />
            <el-option label="事件" value="event" />
            <el-option label="概念" value="concept" />
            <el-option label="产品" value="product" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="editForm.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="活跃" value="active" />
            <el-option label="非活跃" value="inactive" />
            <el-option label="已删除" value="deleted" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveEntity" :loading="saving">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 属性编辑对话框 -->
    <el-dialog v-model="propertyDialogVisible" title="编辑属性" width="500px">
      <el-form :model="propertyForm" :rules="propertyRules" ref="propertyFormRef" label-width="80px">
        <el-form-item label="属性名" prop="name">
          <el-input v-model="propertyForm.name" placeholder="请输入属性名" />
        </el-form-item>
        <el-form-item label="属性类型" prop="type">
          <el-select v-model="propertyForm.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="文本" value="text" />
            <el-option label="数字" value="number" />
            <el-option label="日期" value="date" />
            <el-option label="标签" value="tag" />
            <el-option label="链接" value="url" />
          </el-select>
        </el-form-item>
        <el-form-item label="属性值" prop="value">
          <el-input v-model="propertyForm.value" placeholder="请输入属性值" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="propertyDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveProperty" :loading="saving">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Edit,
  User,
  Plus,
  Delete,
  Refresh,
  Share,
  Right,
  Link,
  Document
} from '@element-plus/icons-vue'

interface EntityData {
  id: string
  name: string
  type: string
  status: string
  description: string
  avatar: string
  createTime: string
  updateTime: string
  creator: string
  documentCount: number
  properties: Property[]
  relations: Relation[]
  documents: DocumentItem[]
  activities: Activity[]
}

interface Property {
  id: string
  name: string
  type: string
  value: any
}

interface Relation {
  id: string
  source: string
  target: string
  targetId: string
  type: string
}

interface DocumentItem {
  id: string
  name: string
  type: string
  size: number
  updateTime: string
  relevance: number
}

interface Activity {
  id: string
  title: string
  description: string
  user: string
  time: string
  type: string
}

const route = useRoute()
const router = useRouter()

const entityId = route.params.id as string

const loading = ref(false)
const propertiesLoading = ref(false)
const relationsLoading = ref(false)
const documentsLoading = ref(false)
const activityLoading = ref(false)
const saving = ref(false)

const editDialogVisible = ref(false)
const propertyDialogVisible = ref(false)

const graphContainer = ref()
const editFormRef = ref()
const propertyFormRef = ref()

const entityData = ref<EntityData>({
  id: '',
  name: '',
  type: '',
  status: '',
  description: '',
  avatar: '',
  createTime: '',
  updateTime: '',
  creator: '',
  documentCount: 0,
  properties: [],
  relations: [],
  documents: [],
  activities: []
})

const editForm = reactive({
  name: '',
  type: '',
  description: '',
  status: ''
})

const propertyForm = reactive({
  id: '',
  name: '',
  type: '',
  value: ''
})

const editRules = {
  name: [
    { required: true, message: '请输入实体名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择实体类型', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

const propertyRules = {
  name: [
    { required: true, message: '请输入属性名', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择属性类型', trigger: 'change' }
  ],
  value: [
    { required: true, message: '请输入属性值', trigger: 'blur' }
  ]
}

// 获取状态类型
const getStatusType = (status: string): string => {
  const typeMap: Record<string, string> = {
    'active': 'success',
    'inactive': 'warning',
    'deleted': 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取活动类型
const getActivityType = (type: string): string => {
  const typeMap: Record<string, string> = {
    'create': 'success',
    'update': 'primary',
    'delete': 'danger',
    'link': 'info'
  }
  return typeMap[type] || 'info'
}

// 格式化日期
const formatDate = (dateString: string): string => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN')
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 编辑实体
const editEntity = () => {
  Object.assign(editForm, {
    name: entityData.value.name,
    type: entityData.value.type,
    description: entityData.value.description,
    status: entityData.value.status
  })
  editDialogVisible.value = true
}

// 保存实体
const saveEntity = async () => {
  if (!editFormRef.value) return
  
  try {
    await editFormRef.value.validate()
    
    saving.value = true
    
    // 这里应该调用实际的API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    Object.assign(entityData.value, editForm)
    
    ElMessage.success('保存成功')
    editDialogVisible.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 添加属性
const addProperty = () => {
  Object.assign(propertyForm, {
    id: '',
    name: '',
    type: '',
    value: ''
  })
  propertyDialogVisible.value = true
}

// 编辑属性
const editProperty = (property: Property) => {
  Object.assign(propertyForm, property)
  propertyDialogVisible.value = true
}

// 保存属性
const saveProperty = async () => {
  if (!propertyFormRef.value) return
  
  try {
    await propertyFormRef.value.validate()
    
    saving.value = true
    
    // 这里应该调用实际的API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    if (propertyForm.id) {
      // 更新属性
      const index = entityData.value.properties.findIndex(p => p.id === propertyForm.id)
      if (index > -1) {
        entityData.value.properties[index] = { ...propertyForm }
      }
    } else {
      // 添加属性
      entityData.value.properties.push({
        ...propertyForm,
        id: Date.now().toString()
      })
    }
    
    ElMessage.success('保存成功')
    propertyDialogVisible.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 删除属性
const deleteProperty = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这个属性吗？', '确认删除', {
      type: 'warning'
    })
    
    const index = entityData.value.properties.findIndex(p => p.id === id)
    if (index > -1) {
      entityData.value.properties.splice(index, 1)
      ElMessage.success('删除成功')
    }
  } catch (error) {
    // 用户取消删除
  }
}

// 刷新关系
const refreshRelations = async () => {
  try {
    relationsLoading.value = true
    
    // 这里应该调用实际的API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('刷新成功')
  } catch (error) {
    ElMessage.error('刷新失败')
  } finally {
    relationsLoading.value = false
  }
}

// 添加关系
const addRelation = () => {
  ElMessage.info('添加关系功能开发中')
}

// 删除关系
const deleteRelation = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这个关系吗？', '确认删除', {
      type: 'warning'
    })
    
    const index = entityData.value.relations.findIndex(r => r.id === id)
    if (index > -1) {
      entityData.value.relations.splice(index, 1)
      ElMessage.success('删除成功')
    }
  } catch (error) {
    // 用户取消删除
  }
}

// 查看相关实体
const viewRelatedEntity = (id: string) => {
  router.push(`/knowledge/entities/detail/${id}`)
}

// 关联文档
const linkDocument = () => {
  ElMessage.info('关联文档功能开发中')
}

// 查看文档
const viewDocument = (id: string) => {
  router.push(`/knowledge/documents/detail/${id}`)
}

// 下载文档
const downloadDocument = (id: string) => {
  ElMessage.success('开始下载文档')
}

// 取消关联文档
const unlinkDocument = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要取消关联这个文档吗？', '确认操作', {
      type: 'warning'
    })
    
    const index = entityData.value.documents.findIndex(d => d.id === id)
    if (index > -1) {
      entityData.value.documents.splice(index, 1)
      ElMessage.success('取消关联成功')
    }
  } catch (error) {
    // 用户取消操作
  }
}

// 获取实体详情
const fetchEntityDetail = async () => {
  try {
    loading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    entityData.value = {
      id: entityId,
      name: '张三',
      type: 'person',
      status: 'active',
      description: '公司技术总监，负责技术架构设计和团队管理',
      avatar: '',
      createTime: '2024-01-15T10:30:00Z',
      updateTime: '2024-01-20T14:20:00Z',
      creator: '管理员',
      documentCount: 15,
      properties: [
        { id: '1', name: '职位', type: 'text', value: '技术总监' },
        { id: '2', name: '部门', type: 'text', value: '技术部' },
        { id: '3', name: '入职时间', type: 'date', value: '2020-03-01' },
        { id: '4', name: '技能标签', type: 'tag', value: 'Java' },
        { id: '5', name: '个人主页', type: 'url', value: 'https://example.com' }
      ],
      relations: [
        { id: '1', source: '张三', target: '技术部', targetId: '2', type: '属于' },
        { id: '2', source: '张三', target: '项目A', targetId: '3', type: '负责' },
        { id: '3', source: '张三', target: '李四', targetId: '4', type: '管理' }
      ],
      documents: [
        {
          id: '1',
          name: '技术架构设计文档.pdf',
          type: 'PDF',
          size: 2048576,
          updateTime: '2024-01-20T10:30:00Z',
          relevance: 4.5
        },
        {
          id: '2',
          name: '团队管理制度.docx',
          type: 'Word',
          size: 1024000,
          updateTime: '2024-01-18T15:20:00Z',
          relevance: 4.0
        }
      ],
      activities: [
        {
          id: '1',
          title: '更新了属性信息',
          description: '修改了职位信息',
          user: '张三',
          time: '2024-01-20T14:20:00Z',
          type: 'update'
        },
        {
          id: '2',
          title: '关联了新文档',
          description: '关联了技术架构设计文档',
          user: '张三',
          time: '2024-01-20T10:30:00Z',
          type: 'link'
        },
        {
          id: '3',
          title: '创建了实体',
          description: '创建了张三这个实体',
          user: '管理员',
          time: '2024-01-15T10:30:00Z',
          type: 'create'
        }
      ]
    }
  } catch (error) {
    ElMessage.error('获取实体详情失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchEntityDetail()
})
</script>

<style scoped>
.entity-detail {
  padding: 20px;
  max-width: 1200px;
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

.entity-info-section {
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

.entity-info {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.entity-avatar {
  flex-shrink: 0;
}

.entity-details {
  flex: 1;
}

.entity-name {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.entity-name h2 {
  margin: 0;
  color: #303133;
}

.entity-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
}

.meta-item .label {
  color: #909399;
  margin-right: 8px;
}

.meta-item .value {
  color: #303133;
  font-weight: 500;
}

.entity-description {
  color: #606266;
  line-height: 1.6;
}

.properties-section,
.relations-section,
.documents-section,
.activity-section {
  margin-bottom: 20px;
}

.properties-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.property-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fafafa;
}

.property-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
}

.property-name {
  font-weight: 500;
  color: #303133;
}

.property-type {
  font-size: 12px;
  color: #909399;
  background-color: #f0f2f5;
  padding: 2px 6px;
  border-radius: 2px;
}

.property-value {
  flex: 1;
  margin: 0 16px;
}

.property-actions {
  display: flex;
  gap: 8px;
}

.empty-properties,
.empty-relations,
.empty-documents,
.empty-activity {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.relations-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  min-height: 400px;
}

.relations-graph {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fafafa;
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
  font-size: 48px;
  margin-bottom: 12px;
}

.relations-list h4 {
  margin: 0 0 16px 0;
  color: #303133;
}

.relation-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.relation-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fafafa;
}

.relation-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.relation-source,
.relation-target {
  font-weight: 500;
  color: #303133;
}

.relation-type {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 14px;
}

.relation-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.document-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fafafa;
}

.document-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.document-icon {
  color: #409eff;
  font-size: 20px;
}

.document-details {
  flex: 1;
}

.document-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.document-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.document-relevance {
  margin-right: 16px;
}

.document-actions {
  display: flex;
  gap: 8px;
}

.activity-timeline {
  min-height: 300px;
}

.activity-content {
  padding: 8px 0;
}

.activity-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.activity-description {
  color: #606266;
  margin-bottom: 4px;
}

.activity-user {
  font-size: 12px;
  color: #909399;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .entity-detail {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .entity-info {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .entity-meta {
    grid-template-columns: 1fr;
  }
  
  .relations-content {
    grid-template-columns: 1fr;
  }
  
  .property-item,
  .relation-item,
  .document-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .property-actions,
  .relation-actions,
  .document-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>