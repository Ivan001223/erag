<template>
  <div class="entity-edit-container">
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
          <h2>{{ isEdit ? '编辑实体' : '查看实体' }}</h2>
          <span class="subtitle">{{ entityData.name || '未命名实体' }}</span>
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
      <!-- 左侧：基本信息 -->
      <el-col :span="16">
        <!-- 基本信息 -->
        <el-card class="info-card">
          <template #header>
            <span>基本信息</span>
          </template>
          <el-form 
            ref="formRef"
            :model="entityData" 
            :rules="formRules"
            label-width="120px"
            :disabled="!isEdit"
          >
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="实体名称" prop="name">
                  <el-input v-model="entityData.name" placeholder="请输入实体名称" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="实体类型" prop="type">
                  <el-select v-model="entityData.type" placeholder="请选择实体类型">
                    <el-option label="人物" value="person" />
                    <el-option label="组织" value="organization" />
                    <el-option label="地点" value="location" />
                    <el-option label="事件" value="event" />
                    <el-option label="概念" value="concept" />
                    <el-option label="产品" value="product" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="状态" prop="status">
                  <el-select v-model="entityData.status" placeholder="请选择状态">
                    <el-option label="活跃" value="active" />
                    <el-option label="草稿" value="draft" />
                    <el-option label="已归档" value="archived" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="置信度" prop="confidence">
                  <el-slider 
                    v-model="entityData.confidence" 
                    :min="0" 
                    :max="100" 
                    show-input
                    :disabled="!isEdit"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="描述" prop="description">
              <el-input 
                v-model="entityData.description" 
                type="textarea" 
                :rows="4"
                placeholder="请输入实体描述"
              />
            </el-form-item>
            <el-form-item label="标签" prop="tags">
              <el-tag
                v-for="tag in entityData.tags"
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
              v-for="(property, index) in entityData.properties" 
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
            <el-empty v-if="entityData.properties.length === 0" description="暂无属性" />
          </div>
        </el-card>

        <!-- 关联关系 -->
        <el-card class="relations-card">
          <template #header>
            <div class="card-header">
              <span>关联关系</span>
              <el-button size="small" @click="showRelationDialog = true">
                <el-icon><Share /></el-icon>
                查看全部
              </el-button>
            </div>
          </template>
          <div class="relations-list">
            <div 
              v-for="relation in entityData.relations.slice(0, 5)" 
              :key="relation.id"
              class="relation-item"
            >
              <div class="relation-content">
                <span class="relation-type">{{ relation.type }}</span>
                <el-icon class="relation-arrow"><Right /></el-icon>
                <span class="relation-target">{{ relation.target }}</span>
              </div>
              <div class="relation-meta">
                <el-tag size="small" type="info">{{ relation.confidence }}%</el-tag>
              </div>
            </div>
            <el-empty v-if="entityData.relations.length === 0" description="暂无关联关系" />
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
              <span class="stat-label">关联关系</span>
              <span class="stat-value">{{ entityData.relations.length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">属性数量</span>
              <span class="stat-value">{{ entityData.properties.length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">引用次数</span>
              <span class="stat-value">{{ entityData.referenceCount || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">创建时间</span>
              <span class="stat-value">{{ entityData.createdAt }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">更新时间</span>
              <span class="stat-value">{{ entityData.updatedAt }}</span>
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
            <el-button class="action-btn" @click="exportEntity">
              <el-icon><Download /></el-icon>
              导出实体
            </el-button>
            <el-button class="action-btn" @click="duplicateEntity">
              <el-icon><CopyDocument /></el-icon>
              复制实体
            </el-button>
            <el-button class="action-btn" type="danger" @click="deleteEntity">
              <el-icon><Delete /></el-icon>
              删除实体
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 关系详情对话框 -->
    <el-dialog v-model="showRelationDialog" title="关联关系" width="800px">
      <el-table :data="entityData.relations" stripe>
        <el-table-column prop="type" label="关系类型" width="120" />
        <el-table-column prop="target" label="目标实体" />
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getConfidenceType(row.confidence)">
              {{ row.confidence }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="150" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" @click="editRelation(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
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
  Share,
  Right,
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
const showRelationDialog = ref(false)

// 实体数据
const entityData = reactive({
  id: '',
  name: '',
  type: 'concept',
  status: 'active',
  confidence: 85,
  description: '',
  tags: [] as string[],
  properties: [] as Array<{ key: string; type: string; value: string }>,
  relations: [] as Array<{ id: string; type: string; target: string; confidence: number; createdAt: string }>,
  referenceCount: 0,
  createdAt: '',
  updatedAt: ''
})

// 原始数据备份
const originalData = ref({})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入实体名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择实体类型', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

// 加载实体数据
const loadEntityData = async () => {
  try {
    const entityId = route.params.id as string
    // 模拟API调用
    const mockData = {
      id: entityId,
      name: '人工智能',
      type: 'concept',
      status: 'active',
      confidence: 92,
      description: '人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于创造能够执行通常需要人类智能的任务的机器。',
      tags: ['技术', '计算机科学', '机器学习'],
      properties: [
        { key: '英文名称', type: 'text', value: 'Artificial Intelligence' },
        { key: '缩写', type: 'text', value: 'AI' },
        { key: '发展年代', type: 'date', value: '1950年代' },
        { key: '主要应用', type: 'text', value: '机器学习、自然语言处理、计算机视觉' }
      ],
      relations: [
        { id: '1', type: '包含', target: '机器学习', confidence: 95, createdAt: '2024-01-15' },
        { id: '2', type: '应用于', target: '自动驾驶', confidence: 88, createdAt: '2024-01-16' },
        { id: '3', type: '相关', target: '深度学习', confidence: 92, createdAt: '2024-01-17' },
        { id: '4', type: '发展自', target: '计算机科学', confidence: 90, createdAt: '2024-01-18' }
      ],
      referenceCount: 156,
      createdAt: '2024-01-15 10:30:00',
      updatedAt: '2024-01-20 16:45:00'
    }
    
    Object.assign(entityData, mockData)
    originalData.value = JSON.parse(JSON.stringify(mockData))
  } catch (error) {
    ElMessage.error('加载实体数据失败')
    console.error('Load entity data error:', error)
  }
}

// 保存实体
const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    saving.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    originalData.value = JSON.parse(JSON.stringify(entityData))
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
  const hasChanges = JSON.stringify(entityData) !== JSON.stringify(originalData.value)
  
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
      
      Object.assign(entityData, originalData.value)
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
  const index = entityData.tags.indexOf(tag)
  if (index > -1) {
    entityData.tags.splice(index, 1)
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
  if (inputValue.value && !entityData.tags.includes(inputValue.value)) {
    entityData.tags.push(inputValue.value)
  }
  inputVisible.value = false
  inputValue.value = ''
}

// 属性管理
const addProperty = () => {
  entityData.properties.push({ key: '', type: 'text', value: '' })
}

const removeProperty = (index: number) => {
  entityData.properties.splice(index, 1)
}

// 置信度类型
const getConfidenceType = (confidence: number) => {
  if (confidence >= 90) return 'success'
  if (confidence >= 70) return 'warning'
  return 'danger'
}

// 操作方法
const viewInGraph = () => {
  ElMessage.info('在图谱中查看功能开发中')
}

const exportEntity = () => {
  ElMessage.info('导出实体功能开发中')
}

const duplicateEntity = () => {
  ElMessage.info('复制实体功能开发中')
}

const deleteEntity = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个实体吗？此操作不可恢复。',
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success('删除成功')
    router.push('/knowledge/entities')
  } catch {
    // 用户取消
  }
}

const editRelation = (relation: any) => {
  ElMessage.info('编辑关系功能开发中')
}

// 组件挂载
onMounted(() => {
  loadEntityData()
})
</script>

<style scoped>
.entity-edit-container {
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
.relations-card,
.stats-card,
.actions-card {
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

.relations-list {
  max-height: 300px;
  overflow-y: auto;
}

.relation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 4px;
}

.relation-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.relation-type {
  font-weight: 500;
  color: #409eff;
}

.relation-arrow {
  color: #909399;
}

.relation-target {
  color: #303133;
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
</style>