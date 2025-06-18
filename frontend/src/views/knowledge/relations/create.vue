<template>
  <div class="create-relation-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <el-button @click="goBack" size="large">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <div class="title-section">
            <h1 class="page-title">
              <el-icon><Connection /></el-icon>
              创建关系
            </h1>
            <p class="page-description">
              在实体之间建立新的关系连接
            </p>
          </div>
        </div>
        <div class="header-right">
          <el-button @click="saveDraft">
            <el-icon><Document /></el-icon>
            保存草稿
          </el-button>
          <el-button type="primary" @click="createRelation" :loading="creating">
            <el-icon><Check /></el-icon>
            创建关系
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 创建表单 -->
    <div class="form-section">
      <el-row :gutter="20">
        <el-col :span="16">
          <el-card shadow="never" class="form-card">
            <template #header>
              <div class="card-header">
                <span>关系信息</span>
                <el-button text @click="resetForm">
                  <el-icon><Refresh /></el-icon>
                  重置
                </el-button>
              </div>
            </template>
            
            <el-form
              ref="formRef"
              :model="form"
              :rules="rules"
              label-width="120px"
              size="large"
            >
              <!-- 关系基本信息 -->
              <div class="form-section-title">
                <el-icon><InfoFilled /></el-icon>
                基本信息
              </div>
              
              <el-form-item label="关系名称" prop="name">
                <el-input
                  v-model="form.name"
                  placeholder="请输入关系名称"
                  clearable
                />
              </el-form-item>
              
              <el-form-item label="关系类型" prop="type">
                <el-select
                  v-model="form.type"
                  placeholder="选择关系类型"
                  style="width: 100%"
                  filterable
                  allow-create
                >
                  <el-option
                    v-for="type in relationTypes"
                    :key="type.value"
                    :label="type.label"
                    :value="type.value"
                  >
                    <div class="option-item">
                      <span>{{ type.label }}</span>
                      <span class="option-desc">{{ type.description }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              
              <el-form-item label="关系描述" prop="description">
                <el-input
                  v-model="form.description"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入关系描述"
                  show-word-limit
                  maxlength="500"
                />
              </el-form-item>
              
              <!-- 实体选择 -->
              <div class="form-section-title">
                <el-icon><User /></el-icon>
                实体选择
              </div>
              
              <el-form-item label="源实体" prop="sourceEntity">
                <el-select
                  v-model="form.sourceEntity"
                  placeholder="选择源实体"
                  style="width: 100%"
                  filterable
                  remote
                  :remote-method="searchEntities"
                  :loading="searchingEntities"
                >
                  <el-option
                    v-for="entity in sourceEntities"
                    :key="entity.id"
                    :label="entity.name"
                    :value="entity.id"
                  >
                    <div class="entity-option">
                      <div class="entity-info">
                        <span class="entity-name">{{ entity.name }}</span>
                        <el-tag size="small" :type="getEntityTypeTagType(entity.type)">
                          {{ entity.type }}
                        </el-tag>
                      </div>
                      <span class="entity-desc">{{ entity.description }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              
              <el-form-item label="目标实体" prop="targetEntity">
                <el-select
                  v-model="form.targetEntity"
                  placeholder="选择目标实体"
                  style="width: 100%"
                  filterable
                  remote
                  :remote-method="searchEntities"
                  :loading="searchingEntities"
                >
                  <el-option
                    v-for="entity in targetEntities"
                    :key="entity.id"
                    :label="entity.name"
                    :value="entity.id"
                  >
                    <div class="entity-option">
                      <div class="entity-info">
                        <span class="entity-name">{{ entity.name }}</span>
                        <el-tag size="small" :type="getEntityTypeTagType(entity.type)">
                          {{ entity.type }}
                        </el-tag>
                      </div>
                      <span class="entity-desc">{{ entity.description }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              
              <!-- 关系属性 -->
              <div class="form-section-title">
                <el-icon><Setting /></el-icon>
                关系属性
              </div>
              
              <el-form-item label="权重" prop="weight">
                <el-slider
                  v-model="form.weight"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  show-tooltip
                  :format-tooltip="formatWeight"
                />
              </el-form-item>
              
              <el-form-item label="方向性">
                <el-radio-group v-model="form.direction">
                  <el-radio label="directed">有向</el-radio>
                  <el-radio label="undirected">无向</el-radio>
                  <el-radio label="bidirectional">双向</el-radio>
                </el-radio-group>
              </el-form-item>
              
              <el-form-item label="置信度" prop="confidence">
                <el-input-number
                  v-model="form.confidence"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  :precision="2"
                  style="width: 200px"
                />
                <span class="form-tip">关系的可信度 (0-1)</span>
              </el-form-item>
              
              <!-- 自定义属性 -->
              <div class="form-section-title">
                <el-icon><Plus /></el-icon>
                自定义属性
                <el-button size="small" @click="addCustomProperty">
                  添加属性
                </el-button>
              </div>
              
              <div v-if="form.customProperties.length > 0" class="custom-properties">
                <div
                  v-for="(property, index) in form.customProperties"
                  :key="index"
                  class="property-item"
                >
                  <el-input
                    v-model="property.key"
                    placeholder="属性名"
                    style="width: 200px; margin-right: 12px;"
                  />
                  <el-select
                    v-model="property.type"
                    style="width: 120px; margin-right: 12px;"
                  >
                    <el-option label="文本" value="string" />
                    <el-option label="数字" value="number" />
                    <el-option label="布尔" value="boolean" />
                    <el-option label="日期" value="date" />
                  </el-select>
                  <el-input
                    v-model="property.value"
                    placeholder="属性值"
                    style="flex: 1; margin-right: 12px;"
                  />
                  <el-button
                    size="small"
                    @click="removeCustomProperty(index)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              
              <!-- 标签 -->
              <el-form-item label="标签">
                <el-select
                  v-model="form.tags"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="添加标签"
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
          </el-card>
        </el-col>
        
        <!-- 右侧预览 -->
        <el-col :span="8">
          <el-card shadow="never" class="preview-card">
            <template #header>
              <div class="card-header">
                <span>关系预览</span>
                <el-button text @click="refreshPreview">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </template>
            
            <!-- 关系图示 -->
            <div class="relation-diagram">
              <div class="entity-node source">
                <div class="node-content">
                  <el-icon><User /></el-icon>
                  <span>{{ getEntityName(form.sourceEntity) || '源实体' }}</span>
                </div>
              </div>
              
              <div class="relation-arrow">
                <div class="arrow-line">
                  <div class="arrow-label">
                    {{ form.name || '关系名称' }}
                  </div>
                </div>
                <div class="arrow-head"></div>
              </div>
              
              <div class="entity-node target">
                <div class="node-content">
                  <el-icon><User /></el-icon>
                  <span>{{ getEntityName(form.targetEntity) || '目标实体' }}</span>
                </div>
              </div>
            </div>
            
            <!-- 关系信息摘要 -->
            <div class="relation-summary">
              <div class="summary-item">
                <span class="label">关系类型:</span>
                <span class="value">{{ form.type || '-' }}</span>
              </div>
              <div class="summary-item">
                <span class="label">方向性:</span>
                <span class="value">{{ getDirectionLabel(form.direction) }}</span>
              </div>
              <div class="summary-item">
                <span class="label">权重:</span>
                <span class="value">{{ form.weight }}</span>
              </div>
              <div class="summary-item">
                <span class="label">置信度:</span>
                <span class="value">{{ form.confidence }}</span>
              </div>
              <div v-if="form.tags.length > 0" class="summary-item">
                <span class="label">标签:</span>
                <div class="tags-container">
                  <el-tag
                    v-for="tag in form.tags"
                    :key="tag"
                    size="small"
                    class="tag-item"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
              </div>
            </div>
            
            <!-- 验证结果 -->
            <div class="validation-section">
              <h4>验证结果</h4>
              <div class="validation-item">
                <el-icon :color="validationResults.entities ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.entities ? 'Check' : 'Close'" />
                </el-icon>
                <span>实体选择</span>
              </div>
              <div class="validation-item">
                <el-icon :color="validationResults.relation ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.relation ? 'Check' : 'Close'" />
                </el-icon>
                <span>关系信息</span>
              </div>
              <div class="validation-item">
                <el-icon :color="validationResults.duplicate ? '#f56c6c' : '#67c23a'">
                  <component :is="validationResults.duplicate ? 'Warning' : 'Check'" />
                </el-icon>
                <span>重复检查</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormRules } from 'element-plus'
import {
  ArrowLeft,
  Document,
  Check,
  Refresh,
  Connection,
  InfoFilled,
  User,
  Setting,
  Plus,
  Delete,
  Close,
  Warning
} from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref()
const creating = ref(false)
const searchingEntities = ref(false)

// 表单数据
const form = reactive({
  name: '',
  type: '',
  description: '',
  sourceEntity: '',
  targetEntity: '',
  weight: 0.5,
  direction: 'directed',
  confidence: 0.8,
  customProperties: [],
  tags: []
})

// 表单验证规则
const rules: FormRules = {
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
  confidence: [
    { required: true, message: '请输入置信度', trigger: 'blur' },
    { type: 'number', min: 0, max: 1, message: '置信度必须在 0-1 之间', trigger: 'blur' }
  ]
}

// 关系类型
const relationTypes = ref([
  {
    value: 'belongs_to',
    label: '属于',
    description: '表示从属关系'
  },
  {
    value: 'contains',
    label: '包含',
    description: '表示包含关系'
  },
  {
    value: 'related_to',
    label: '相关',
    description: '表示相关关系'
  },
  {
    value: 'depends_on',
    label: '依赖',
    description: '表示依赖关系'
  },
  {
    value: 'implements',
    label: '实现',
    description: '表示实现关系'
  },
  {
    value: 'inherits',
    label: '继承',
    description: '表示继承关系'
  },
  {
    value: 'uses',
    label: '使用',
    description: '表示使用关系'
  },
  {
    value: 'creates',
    label: '创建',
    description: '表示创建关系'
  }
])

// 实体数据
const sourceEntities = ref([])
const targetEntities = ref([])
const availableTags = ref([
  '重要',
  '核心',
  '临时',
  '系统',
  '业务',
  '技术'
])

// 验证结果
const validationResults = computed(() => {
  return {
    entities: form.sourceEntity && form.targetEntity && form.sourceEntity !== form.targetEntity,
    relation: form.name && form.type,
    duplicate: false // 这里应该检查是否存在重复关系
  }
})

// 方法
const goBack = () => {
  router.back()
}

const formatWeight = (value: number) => {
  return `权重: ${value}`
}

const getEntityTypeTagType = (type: string) => {
  const types = {
    person: 'primary',
    organization: 'success',
    concept: 'warning',
    technology: 'info',
    product: 'danger'
  }
  return types[type] || 'info'
}

const getEntityName = (entityId: string) => {
  const allEntities = [...sourceEntities.value, ...targetEntities.value]
  const entity = allEntities.find(e => e.id === entityId)
  return entity?.name || ''
}

const getDirectionLabel = (direction: string) => {
  const labels = {
    directed: '有向',
    undirected: '无向',
    bidirectional: '双向'
  }
  return labels[direction] || direction
}

const searchEntities = async (query: string) => {
  if (!query) return
  
  searchingEntities.value = true
  try {
    // 这里调用搜索实体的API
    // const response = await entityApi.search({ query })
    // sourceEntities.value = response.data
    // targetEntities.value = response.data
    
    // 模拟数据
    const mockEntities = [
      {
        id: '1',
        name: '人工智能',
        type: 'concept',
        description: '计算机科学的一个分支'
      },
      {
        id: '2',
        name: '机器学习',
        type: 'technology',
        description: '实现人工智能的技术手段'
      },
      {
        id: '3',
        name: '深度学习',
        type: 'technology',
        description: '机器学习的一个子领域'
      }
    ].filter(entity => entity.name.includes(query))
    
    sourceEntities.value = mockEntities
    targetEntities.value = mockEntities
    
  } catch (error) {
    ElMessage.error('搜索实体失败')
  } finally {
    searchingEntities.value = false
  }
}

const addCustomProperty = () => {
  form.customProperties.push({
    key: '',
    type: 'string',
    value: ''
  })
}

const removeCustomProperty = (index: number) => {
  form.customProperties.splice(index, 1)
}

const resetForm = () => {
  formRef.value?.resetFields()
  form.customProperties = []
  form.tags = []
}

const refreshPreview = () => {
  ElMessage.info('预览已刷新')
}

const saveDraft = async () => {
  try {
    // 这里调用保存草稿的API
    ElMessage.success('草稿已保存')
  } catch (error) {
    ElMessage.error('保存草稿失败')
  }
}

const createRelation = async () => {
  try {
    const valid = await formRef.value?.validate()
    if (!valid) return
    
    if (!validationResults.value.entities) {
      ElMessage.warning('请选择不同的源实体和目标实体')
      return
    }
    
    creating.value = true
    
    // 这里调用创建关系的API
    // const response = await relationApi.create({
    //   ...form,
    //   customProperties: form.customProperties.filter(p => p.key && p.value)
    // })
    
    // 模拟创建延迟
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    ElMessage.success('关系创建成功')
    router.push('/knowledge/relations')
    
  } catch (error) {
    ElMessage.error('创建关系失败，请重试')
  } finally {
    creating.value = false
  }
}

// 监听实体选择变化
watch([() => form.sourceEntity, () => form.targetEntity], () => {
  // 检查重复关系
  if (form.sourceEntity && form.targetEntity) {
    // 这里可以调用API检查是否存在重复关系
  }
})

// 生命周期
onMounted(() => {
  // 初始化数据
  searchEntities('')
})
</script>

<style scoped>
.create-relation-page {
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
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.title-section {
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

.form-section {
  margin-bottom: 20px;
}

.form-card,
.preview-card {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #374151;
  margin: 24px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.option-item {
  display: flex;
  flex-direction: column;
}

.option-desc {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.entity-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.entity-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.entity-name {
  font-weight: 500;
}

.entity-desc {
  font-size: 12px;
  color: #6b7280;
}

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #6b7280;
}

.custom-properties {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.property-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.relation-diagram {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  margin-bottom: 20px;
  background: #f8fafc;
  border-radius: 8px;
}

.entity-node {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 60px;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.entity-node.source {
  border-color: #3b82f6;
}

.entity-node.target {
  border-color: #10b981;
}

.node-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  text-align: center;
}

.relation-arrow {
  display: flex;
  align-items: center;
  margin: 0 20px;
  position: relative;
}

.arrow-line {
  width: 80px;
  height: 2px;
  background: #6b7280;
  position: relative;
}

.arrow-label {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #374151;
  background: white;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.arrow-head {
  width: 0;
  height: 0;
  border-left: 8px solid #6b7280;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
}

.relation-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-item .label {
  font-weight: 500;
  color: #374151;
  min-width: 60px;
}

.summary-item .value {
  color: #6b7280;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-item {
  margin: 0;
}

.validation-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.validation-section h4 {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 12px 0;
}

.validation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 14px;
}

@media (max-width: 768px) {
  .create-relation-page {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .header-left {
    flex-direction: column;
    gap: 12px;
  }
  
  .form-section .el-col {
    margin-bottom: 20px;
  }
  
  .relation-diagram {
    flex-direction: column;
    gap: 16px;
  }
  
  .relation-arrow {
    transform: rotate(90deg);
    margin: 0;
  }
  
  .property-item {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>