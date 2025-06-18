<template>
  <div class="create-entity-page">
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
              <el-icon><User /></el-icon>
              创建实体
            </h1>
            <p class="page-description">
              添加新的知识实体到知识图谱中
            </p>
          </div>
        </div>
        <div class="header-right">
          <el-button @click="saveDraft">
            <el-icon><Document /></el-icon>
            保存草稿
          </el-button>
          <el-button type="primary" @click="createEntity" :loading="creating">
            <el-icon><Check /></el-icon>
            创建实体
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
                <span>实体信息</span>
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
              <!-- 基本信息 -->
              <div class="form-section-title">
                <el-icon><InfoFilled /></el-icon>
                基本信息
              </div>
              
              <el-form-item label="实体名称" prop="name">
                <el-input
                  v-model="form.name"
                  placeholder="请输入实体名称"
                  clearable
                  show-word-limit
                  maxlength="100"
                />
              </el-form-item>
              
              <el-form-item label="实体类型" prop="type">
                <el-select
                  v-model="form.type"
                  placeholder="选择实体类型"
                  style="width: 100%"
                  filterable
                  allow-create
                >
                  <el-option
                    v-for="type in entityTypes"
                    :key="type.value"
                    :label="type.label"
                    :value="type.value"
                  >
                    <div class="option-item">
                      <el-icon :color="type.color">
                        <component :is="type.icon" />
                      </el-icon>
                      <span>{{ type.label }}</span>
                      <span class="option-desc">{{ type.description }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              
              <el-form-item label="实体描述" prop="description">
                <el-input
                  v-model="form.description"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入实体描述"
                  show-word-limit
                  maxlength="1000"
                />
              </el-form-item>
              
              <el-form-item label="别名">
                <el-select
                  v-model="form.aliases"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="添加实体别名"
                  style="width: 100%"
                >
                  <el-option
                    v-for="alias in suggestedAliases"
                    :key="alias"
                    :label="alias"
                    :value="alias"
                  />
                </el-select>
              </el-form-item>
              
              <!-- 分类信息 -->
              <div class="form-section-title">
                <el-icon><FolderOpened /></el-icon>
                分类信息
              </div>
              
              <el-form-item label="所属领域">
                <el-cascader
                  v-model="form.domain"
                  :options="domainOptions"
                  :props="{ expandTrigger: 'hover' }"
                  placeholder="选择所属领域"
                  style="width: 100%"
                  filterable
                />
              </el-form-item>
              
              <el-form-item label="重要程度">
                <el-rate
                  v-model="form.importance"
                  :max="5"
                  show-text
                  :texts="['很低', '较低', '一般', '重要', '非常重要']"
                />
              </el-form-item>
              
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
              
              <!-- 属性信息 -->
              <div class="form-section-title">
                <el-icon><Setting /></el-icon>
                属性信息
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
                    <el-option label="URL" value="url" />
                    <el-option label="邮箱" value="email" />
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
              
              <!-- 来源信息 -->
              <div class="form-section-title">
                <el-icon><Link /></el-icon>
                来源信息
              </div>
              
              <el-form-item label="数据来源">
                <el-input
                  v-model="form.source"
                  placeholder="请输入数据来源"
                  clearable
                />
              </el-form-item>
              
              <el-form-item label="参考链接">
                <el-input
                  v-model="form.referenceUrl"
                  placeholder="请输入参考链接"
                  clearable
                />
              </el-form-item>
              
              <el-form-item label="置信度" prop="confidence">
                <el-slider
                  v-model="form.confidence"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  show-tooltip
                  :format-tooltip="formatConfidence"
                />
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
        
        <!-- 右侧预览 -->
        <el-col :span="8">
          <el-card shadow="never" class="preview-card">
            <template #header>
              <div class="card-header">
                <span>实体预览</span>
                <el-button text @click="refreshPreview">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </template>
            
            <!-- 实体卡片预览 -->
            <div class="entity-preview">
              <div class="entity-card">
                <div class="entity-header">
                  <div class="entity-icon">
                    <el-icon :color="getEntityTypeColor(form.type)">
                      <component :is="getEntityTypeIcon(form.type)" />
                    </el-icon>
                  </div>
                  <div class="entity-info">
                    <h3 class="entity-name">{{ form.name || '实体名称' }}</h3>
                    <el-tag
                      v-if="form.type"
                      size="small"
                      :type="getEntityTypeTagType(form.type)"
                    >
                      {{ getEntityTypeLabel(form.type) }}
                    </el-tag>
                  </div>
                  <div class="entity-rating">
                    <el-rate
                      v-model="form.importance"
                      disabled
                      size="small"
                    />
                  </div>
                </div>
                
                <div class="entity-description">
                  {{ form.description || '暂无描述' }}
                </div>
                
                <div v-if="form.aliases.length > 0" class="entity-aliases">
                  <span class="label">别名:</span>
                  <div class="aliases-list">
                    <el-tag
                      v-for="alias in form.aliases"
                      :key="alias"
                      size="small"
                      effect="plain"
                      class="alias-tag"
                    >
                      {{ alias }}
                    </el-tag>
                  </div>
                </div>
                
                <div v-if="form.tags.length > 0" class="entity-tags">
                  <span class="label">标签:</span>
                  <div class="tags-list">
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
                
                <div v-if="form.customProperties.length > 0" class="entity-properties">
                  <span class="label">属性:</span>
                  <div class="properties-list">
                    <div
                      v-for="property in form.customProperties.filter(p => p.key && p.value)"
                      :key="property.key"
                      class="property-item"
                    >
                      <span class="property-key">{{ property.key }}:</span>
                      <span class="property-value">{{ property.value }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 统计信息 -->
            <div class="stats-section">
              <h4>统计信息</h4>
              <div class="stats-grid">
                <div class="stat-item">
                  <span class="stat-label">字符数</span>
                  <span class="stat-value">{{ (form.name + form.description).length }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">别名数</span>
                  <span class="stat-value">{{ form.aliases.length }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">标签数</span>
                  <span class="stat-value">{{ form.tags.length }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">属性数</span>
                  <span class="stat-value">{{ form.customProperties.filter(p => p.key && p.value).length }}</span>
                </div>
              </div>
            </div>
            
            <!-- 验证结果 -->
            <div class="validation-section">
              <h4>验证结果</h4>
              <div class="validation-item">
                <el-icon :color="validationResults.name ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.name ? 'Check' : 'Close'" />
                </el-icon>
                <span>实体名称</span>
              </div>
              <div class="validation-item">
                <el-icon :color="validationResults.type ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.type ? 'Check' : 'Close'" />
                </el-icon>
                <span>实体类型</span>
              </div>
              <div class="validation-item">
                <el-icon :color="validationResults.description ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.description ? 'Check' : 'Close'" />
                </el-icon>
                <span>实体描述</span>
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
import { ref, reactive, computed, onMounted } from 'vue'
import type { FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Document,
  Check,
  Refresh,
  User,
  InfoFilled,
  FolderOpened,
  Setting,
  Link,
  Delete,
  Close,
  Warning,
  Avatar,
  OfficeBuilding,
  Cpu,
  ShoppingBag,
  Reading
} from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref()
const creating = ref(false)

// 表单数据
const form = reactive({
  name: '',
  type: '',
  description: '',
  aliases: [],
  domain: [],
  importance: 3,
  tags: [],
  customProperties: [],
  source: '',
  referenceUrl: '',
  confidence: 0.8
})

// 表单验证规则
const rules: FormRules = {
  name: [
    { required: true, message: '请输入实体名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择实体类型', trigger: 'change' }
  ],
  description: [
    { required: true, message: '请输入实体描述', trigger: 'blur' },
    { min: 10, max: 1000, message: '长度在 10 到 1000 个字符', trigger: 'blur' }
  ],
  confidence: [
    { required: true, message: '请设置置信度', trigger: 'blur' },
    { type: 'number', min: 0, max: 1, message: '置信度必须在 0-1 之间', trigger: 'blur' }
  ]
}

// 实体类型
const entityTypes = ref([
  {
    value: 'person',
    label: '人物',
    description: '个人、角色等',
    icon: 'Avatar',
    color: '#409eff'
  },
  {
    value: 'organization',
    label: '组织',
    description: '公司、机构等',
    icon: 'OfficeBuilding',
    color: '#67c23a'
  },
  {
    value: 'concept',
    label: '概念',
    description: '抽象概念、理论等',
    icon: 'Reading',
    color: '#e6a23c'
  },
  {
    value: 'technology',
    label: '技术',
    description: '技术、工具等',
    icon: 'Cpu',
    color: '#f56c6c'
  },
  {
    value: 'product',
    label: '产品',
    description: '产品、服务等',
    icon: 'ShoppingBag',
    color: '#909399'
  }
])

// 领域选项
const domainOptions = ref([
  {
    value: 'technology',
    label: '技术',
    children: [
      { value: 'ai', label: '人工智能' },
      { value: 'web', label: 'Web开发' },
      { value: 'mobile', label: '移动开发' },
      { value: 'data', label: '数据科学' }
    ]
  },
  {
    value: 'business',
    label: '商业',
    children: [
      { value: 'finance', label: '金融' },
      { value: 'marketing', label: '市场营销' },
      { value: 'management', label: '管理' }
    ]
  },
  {
    value: 'science',
    label: '科学',
    children: [
      { value: 'physics', label: '物理学' },
      { value: 'chemistry', label: '化学' },
      { value: 'biology', label: '生物学' }
    ]
  }
])

// 可用标签
const availableTags = ref([
  '重要',
  '核心',
  '基础',
  '高级',
  '热门',
  '新兴',
  '传统',
  '实用'
])

// 建议别名
const suggestedAliases = ref([])

// 验证结果
const validationResults = computed(() => {
  return {
    name: form.name.length >= 2,
    type: !!form.type,
    description: form.description.length >= 10,
    duplicate: false // 这里应该检查是否存在重复实体
  }
})

// 方法
const goBack = () => {
  router.back()
}

const formatConfidence = (value: number) => {
  return `置信度: ${(value * 100).toFixed(0)}%`
}

const getEntityTypeColor = (type: string) => {
  const typeObj = entityTypes.value.find(t => t.value === type)
  return typeObj?.color || '#909399'
}

const getEntityTypeIcon = (type: string) => {
  const typeObj = entityTypes.value.find(t => t.value === type)
  return typeObj?.icon || 'User'
}

const getEntityTypeLabel = (type: string) => {
  const typeObj = entityTypes.value.find(t => t.value === type)
  return typeObj?.label || type
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
  form.aliases = []
  form.domain = []
  form.tags = []
  form.customProperties = []
  form.importance = 3
  form.confidence = 0.8
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

const createEntity = async () => {
  try {
    const valid = await formRef.value?.validate()
    if (!valid) return
    
    creating.value = true
    
    // 这里调用创建实体的API
    // const response = await entityApi.create({
    //   ...form,
    //   customProperties: form.customProperties.filter(p => p.key && p.value)
    // })
    
    // 模拟创建延迟
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    ElMessage.success('实体创建成功')
    router.push('/knowledge/entities')
    
  } catch (error) {
    ElMessage.error('创建实体失败，请重试')
  } finally {
    creating.value = false
  }
}

// 生命周期
onMounted(() => {
  // 初始化数据
})
</script>

<style scoped>
.create-entity-page {
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
  align-items: center;
  gap: 8px;
}

.option-desc {
  font-size: 12px;
  color: #6b7280;
  margin-left: auto;
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

.entity-preview {
  margin-bottom: 20px;
}

.entity-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: white;
}

.entity-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.entity-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 8px;
  font-size: 20px;
}

.entity-info {
  flex: 1;
}

.entity-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px 0;
}

.entity-rating {
  margin-left: auto;
}

.entity-description {
  color: #6b7280;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 12px;
}

.entity-aliases,
.entity-tags,
.entity-properties {
  margin-bottom: 12px;
}

.label {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  display: block;
  margin-bottom: 4px;
}

.aliases-list,
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.alias-tag,
.tag-item {
  margin: 0;
}

.properties-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.property-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.property-key {
  font-weight: 500;
  color: #374151;
}

.property-value {
  color: #6b7280;
}

.stats-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
  margin-bottom: 16px;
}

.stats-section h4 {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 12px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.stat-label {
  color: #6b7280;
}

.stat-value {
  font-weight: 500;
  color: #374151;
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
  .create-entity-page {
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
  
  .property-item {
    flex-direction: column;
    align-items: stretch;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>