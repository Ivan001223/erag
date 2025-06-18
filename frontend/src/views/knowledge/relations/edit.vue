<template>
  <div class="relation-edit-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button 
          type="text" 
          @click="$router.go(-1)"
          class="back-btn"
        >
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div class="header-title">
          <h2>{{ isEdit ? '编辑关系' : '查看关系' }}</h2>
          <span class="subtitle">{{ relationData.name || '未命名关系' }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button v-if="!isEdit" @click="isEdit = true" type="primary">
          <el-icon><Edit /></el-icon>
          编辑
        </el-button>
        <template v-else>
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" @click="handleSave" :loading="saving">
            <el-icon><Check /></el-icon>
            保存
          </el-button>
        </template>
      </div>
    </div>

    <el-row :gutter="20">
      <!-- 左侧：关系信息 -->
      <el-col :span="16">
        <!-- 基本信息 -->
        <el-card class="info-card">
          <template #header>
            <span>基本信息</span>
          </template>
          <el-form 
            ref="formRef"
            :model="relationData" 
            :rules="formRules"
            label-width="120px"
            :disabled="!isEdit"
          >
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="关系名称" prop="name">
                  <el-input v-model="relationData.name" placeholder="请输入关系名称" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="关系类型" prop="type">
                  <el-select v-model="relationData.type" placeholder="请选择关系类型">
                    <el-option label="包含" value="contains" />
                    <el-option label="属于" value="belongs_to" />
                    <el-option label="相关" value="related_to" />
                    <el-option label="依赖" value="depends_on" />
                    <el-option label="影响" value="affects" />
                    <el-option label="产生" value="produces" />
                    <el-option label="使用" value="uses" />
                    <el-option label="继承" value="inherits" />
                    <el-option label="实现" value="implements" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="源实体" prop="sourceEntity">
                  <el-select 
                    v-model="relationData.sourceEntity" 
                    placeholder="请选择源实体"
                    filterable
                    remote
                    :remote-method="searchEntities"
                    :loading="entityLoading"
                  >
                    <el-option
                      v-for="entity in entityOptions"
                      :key="entity.id"
                      :label="entity.name"
                      :value="entity.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="目标实体" prop="targetEntity">
                  <el-select 
                    v-model="relationData.targetEntity" 
                    placeholder="请选择目标实体"
                    filterable
                    remote
                    :remote-method="searchEntities"
                    :loading="entityLoading"
                  >
                    <el-option
                      v-for="entity in entityOptions"
                      :key="entity.id"
                      :label="entity.name"
                      :value="entity.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="状态" prop="status">
                  <el-select v-model="relationData.status" placeholder="请选择状态">
                    <el-option label="活跃" value="active" />
                    <el-option label="草稿" value="draft" />
                    <el-option label="已归档" value="archived" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="置信度" prop="confidence">
                  <el-slider 
                    v-model="relationData.confidence" 
                    :min="0" 
                    :max="100" 
                    show-input
                    :disabled="!isEdit"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="权重" prop="weight">
                  <el-input-number 
                    v-model="relationData.weight" 
                    :min="0" 
                    :max="10" 
                    :step="0.1"
                    :precision="1"
                    :disabled="!isEdit"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="方向性" prop="direction">
                  <el-select v-model="relationData.direction" placeholder="请选择方向性">
                    <el-option label="单向" value="directed" />
                    <el-option label="双向" value="undirected" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="描述" prop="description">
              <el-input 
                v-model="relationData.description" 
                type="textarea" 
                :rows="4"
                placeholder="请输入关系描述"
              />
            </el-form-item>
            <el-form-item label="标签" prop="tags">
              <el-tag
                v-for="tag in relationData.tags"
                :key="tag"
                closable
                @close="removeTag(tag)"
                class="tag-item"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-if="inputVisible"
                ref="inputRef"
                v-model="inputValue"
                class="tag-input"
                size="small"
                @keyup.enter="handleInputConfirm"
                @blur="handleInputConfirm"
              />
              <el-button v-else class="button-new-tag" size="small" @click="showInput">
                + 新标签
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 属性信息 -->
        <el-card class="properties-card">
          <template #header>
            <div class="card-header">
              <span>属性信息</span>
              <el-button v-if="isEdit" size="small" @click="addProperty">
                <el-icon><Plus /></el-icon>
                添加属性
              </el-button>
            </div>
          </template>
          <div class="properties-list">
            <div 
              v-for="(property, index) in relationData.properties" 
              :key="index"
              class="property-item"
            >
              <el-row :gutter="12" align="middle">
                <el-col :span="6">
                  <el-input 
                    v-model="property.key" 
                    placeholder="属性名"
                    :disabled="!isEdit"
                  />
                </el-col>
                <el-col :span="6">
                  <el-select 
                    v-model="property.type" 
                    placeholder="类型"
                    :disabled="!isEdit"
                  >
                    <el-option label="文本" value="text" />
                    <el-option label="数字" value="number" />
                    <el-option label="日期" value="date" />
                    <el-option label="布尔" value="boolean" />
                    <el-option label="链接" value="url" />
                  </el-select>
                </el-col>
                <el-col :span="8">
                  <el-input 
                    v-model="property.value" 
                    placeholder="属性值"
                    :disabled="!isEdit"
                  />
                </el-col>
                <el-col :span="4">
                  <el-button 
                    v-if="isEdit"
                    type="danger" 
                    size="small" 
                    @click="removeProperty(index)"
                    text
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-col>
              </el-row>
            </div>
            <el-empty v-if="relationData.properties.length === 0" description="暂无属性" />
          </div>
        </el-card>

        <!-- 关系可视化 -->
        <el-card class="visualization-card">
          <template #header>
            <div class="card-header">
              <span>关系可视化</span>
              <el-button size="small" @click="refreshVisualization">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          <div class="relation-visualization">
            <div class="relation-graph">
              <div class="entity-node source-node">
                <div class="node-content">
                  <el-icon><User /></el-icon>
                  <span>{{ getEntityName(relationData.sourceEntity) }}</span>
                </div>
              </div>
              <div class="relation-edge">
                <div class="edge-line">
                  <el-icon class="edge-arrow"><Right /></el-icon>
                </div>
                <div class="edge-label">{{ relationData.name }}</div>
              </div>
              <div class="entity-node target-node">
                <div class="node-content">
                  <el-icon><User /></el-icon>
                  <span>{{ getEntityName(relationData.targetEntity) }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：统计和操作 -->
      <el-col :span="8">
        <!-- 统计信息 -->
        <el-card class="stats-card">
          <template #header>
            <span>统计信息</span>
          </template>
          <div class="stats-list">
            <div class="stat-item">
              <span class="stat-label">置信度</span>
              <span class="stat-value">{{ relationData.confidence }}%</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">权重</span>
              <span class="stat-value">{{ relationData.weight }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">属性数量</span>
              <span class="stat-value">{{ relationData.properties.length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">引用次数</span>
              <span class="stat-value">{{ relationData.referenceCount || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">创建时间</span>
              <span class="stat-value">{{ relationData.createdAt }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">更新时间</span>
              <span class="stat-value">{{ relationData.updatedAt }}</span>
            </div>
          </div>
        </el-card>

        <!-- 操作面板 -->
        <el-card class="actions-card">
          <template #header>
            <span>操作</span>
          </template>
          <div class="actions-list">
            <el-button class="action-btn" @click="viewInGraph">
              <el-icon><PictureRounded /></el-icon>
              在图谱中查看
            </el-button>
            <el-button class="action-btn" @click="exportRelation">
              <el-icon><Download /></el-icon>
              导出关系
            </el-button>
            <el-button class="action-btn" @click="duplicateRelation">
              <el-icon><CopyDocument /></el-icon>
              复制关系
            </el-button>
            <el-button class="action-btn" type="danger" @click="deleteRelation">
              <el-icon><Delete /></el-icon>
              删除关系
            </el-button>
          </div>
        </el-card>

        <!-- 相关关系 -->
        <el-card class="related-card">
          <template #header>
            <span>相关关系</span>
          </template>
          <div class="related-list">
            <div 
              v-for="related in relationData.relatedRelations" 
              :key="related.id"
              class="related-item"
            >
              <div class="related-content">
                <span class="related-name">{{ related.name }}</span>
                <span class="related-type">{{ related.type }}</span>
              </div>
              <el-tag size="small" :type="getConfidenceType(related.confidence)">
                {{ related.confidence }}%
              </el-tag>
            </div>
            <el-empty v-if="relationData.relatedRelations.length === 0" description="暂无相关关系" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  ArrowLeft,
  Edit,
  Check,
  Plus,
  Delete,
  Refresh,
  Right,
  User,
  PictureRounded,
  Download,
  CopyDocument
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 表单引用
const formRef = ref<FormInstance>()
const inputRef = ref<HTMLInputElement>()

// 状态
const isEdit = ref(false)
const saving = ref(false)
const inputVisible = ref(false)
const inputValue = ref('')
const entityLoading = ref(false)

// 实体选项
const entityOptions = ref<Array<{ id: string; name: string }>>([])

// 关系数据
const relationData = reactive({
  id: '',
  name: '',
  type: 'related_to',
  sourceEntity: '',
  targetEntity: '',
  status: 'active',
  confidence: 85,
  weight: 1.0,
  direction: 'directed',
  description: '',
  tags: [] as string[],
  properties: [] as Array<{ key: string; type: string; value: string }>,
  relatedRelations: [] as Array<{ id: string; name: string; type: string; confidence: number }>,
  referenceCount: 0,
  createdAt: '',
  updatedAt: ''
})

// 原始数据备份
const originalData = ref({})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入关系名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择关系类型', trigger: 'change' }
  ],
  sourceEntity: [
    { required: true, message: '请选择源实体', trigger: 'change' }
  ],
  targetEntity: [
    { required: true, message: '请选择目标实体', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

// 加载关系数据
const loadRelationData = async () => {
  try {
    const relationId = route.params.id as string
    // 模拟API调用
    const mockData = {
      id: relationId,
      name: '包含关系',
      type: 'contains',
      sourceEntity: '1',
      targetEntity: '2',
      status: 'active',
      confidence: 92,
      weight: 1.5,
      direction: 'directed',
      description: '人工智能包含机器学习这一重要分支。',
      tags: ['核心关系', '技术'],
      properties: [
        { key: '关系强度', type: 'number', value: '0.9' },
        { key: '确认来源', type: 'text', value: '学术文献' },
        { key: '建立时间', type: 'date', value: '2024-01-15' }
      ],
      relatedRelations: [
        { id: '3', name: '应用关系', type: 'applies_to', confidence: 88 },
        { id: '4', name: '发展关系', type: 'develops_from', confidence: 85 }
      ],
      referenceCount: 45,
      createdAt: '2024-01-15 10:30:00',
      updatedAt: '2024-01-20 16:45:00'
    }
    
    Object.assign(relationData, mockData)
    originalData.value = JSON.parse(JSON.stringify(mockData))
    
    // 加载实体选项
    await loadEntityOptions()
  } catch (error) {
    ElMessage.error('加载关系数据失败')
    console.error('Load relation data error:', error)
  }
}

// 加载实体选项
const loadEntityOptions = async () => {
  try {
    // 模拟API调用
    entityOptions.value = [
      { id: '1', name: '人工智能' },
      { id: '2', name: '机器学习' },
      { id: '3', name: '深度学习' },
      { id: '4', name: '自然语言处理' },
      { id: '5', name: '计算机视觉' }
    ]
  } catch (error) {
    console.error('Load entity options error:', error)
  }
}

// 搜索实体
const searchEntities = async (query: string) => {
  if (!query) return
  
  entityLoading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 300))
    // 这里应该调用实际的搜索API
  } catch (error) {
    console.error('Search entities error:', error)
  } finally {
    entityLoading.value = false
  }
}

// 获取实体名称
const getEntityName = (entityId: string) => {
  const entity = entityOptions.value.find(e => e.id === entityId)
  return entity?.name || '未知实体'
}

// 保存关系
const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    saving.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    originalData.value = JSON.parse(JSON.stringify(relationData))
    isEdit.value = false
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('Save error:', error)
  } finally {
    saving.value = false
  }
}

// 取消编辑
const handleCancel = async () => {
  const hasChanges = JSON.stringify(relationData) !== JSON.stringify(originalData.value)
  
  if (hasChanges) {
    try {
      await ElMessageBox.confirm(
        '您有未保存的更改，确定要取消吗？',
        '确认取消',
        {
          confirmButtonText: '确定',
          cancelButtonText: '继续编辑',
          type: 'warning'
        }
      )
      
      Object.assign(relationData, originalData.value)
      isEdit.value = false
    } catch {
      // 用户取消
    }
  } else {
    isEdit.value = false
  }
}

// 标签管理
const removeTag = (tag: string) => {
  if (!isEdit.value) return
  const index = relationData.tags.indexOf(tag)
  if (index > -1) {
    relationData.tags.splice(index, 1)
  }
}

const showInput = () => {
  if (!isEdit.value) return
  inputVisible.value = true
  nextTick(() => {
    inputRef.value?.focus()
  })
}

const handleInputConfirm = () => {
  if (inputValue.value && !relationData.tags.includes(inputValue.value)) {
    relationData.tags.push(inputValue.value)
  }
  inputVisible.value = false
  inputValue.value = ''
}

// 属性管理
const addProperty = () => {
  relationData.properties.push({ key: '', type: 'text', value: '' })
}

const removeProperty = (index: number) => {
  relationData.properties.splice(index, 1)
}

// 置信度类型
const getConfidenceType = (confidence: number) => {
  if (confidence >= 90) return 'success'
  if (confidence >= 70) return 'warning'
  return 'danger'
}

// 刷新可视化
const refreshVisualization = () => {
  ElMessage.info('刷新关系可视化')
}

// 操作方法
const viewInGraph = () => {
  ElMessage.info('在图谱中查看功能开发中')
}

const exportRelation = () => {
  ElMessage.info('导出关系功能开发中')
}

const duplicateRelation = () => {
  ElMessage.info('复制关系功能开发中')
}

const deleteRelation = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个关系吗？此操作不可恢复。',
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('删除成功')
    router.push('/knowledge/relations')
  } catch {
    // 用户取消
  }
}

// 组件挂载
onMounted(() => {
  loadRelationData()
})
</script>

<style scoped>
.relation-edit-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
}

.header-title h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.subtitle {
  color: #909399;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.info-card,
.properties-card,
.visualization-card,
.stats-card,
.actions-card,
.related-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tag-item {
  margin-right: 8px;
  margin-bottom: 8px;
}

.tag-input {
  width: 90px;
  margin-right: 8px;
  vertical-align: bottom;
}

.button-new-tag {
  height: 24px;
  line-height: 22px;
  padding-top: 0;
  padding-bottom: 0;
}

.properties-list {
  max-height: 400px;
  overflow-y: auto;
}

.property-item {
  margin-bottom: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 4px;
}

.relation-visualization {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 4px;
}

.relation-graph {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
}

.entity-node {
  padding: 16px 20px;
  background: white;
  border: 2px solid #409eff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #303133;
}

.relation-edge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.edge-line {
  display: flex;
  align-items: center;
  color: #409eff;
  font-size: 24px;
}

.edge-label {
  padding: 4px 8px;
  background: #409eff;
  color: white;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
}

.stats-list {
  space-y: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #606266;
  font-size: 14px;
}

.stat-value {
  color: #303133;
  font-weight: 500;
}

.actions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  width: 100%;
  justify-content: flex-start;
}

.related-list {
  max-height: 300px;
  overflow-y: auto;
}

.related-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 4px;
}

.related-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.related-name {
  font-weight: 500;
  color: #303133;
}

.related-type {
  font-size: 12px;
  color: #909399;
}
</style>