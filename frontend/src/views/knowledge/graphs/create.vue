<template>
  <div class="create-graph-page">
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
              <el-icon><Share /></el-icon>
              创建知识图谱
            </h1>
            <p class="page-description">
              创建新的知识图谱项目
            </p>
          </div>
        </div>
        <div class="header-right">
          <el-button @click="saveDraft">
            <el-icon><Document /></el-icon>
            保存草稿
          </el-button>
          <el-button type="primary" @click="createGraph" :loading="creating">
            <el-icon><Check /></el-icon>
            创建图谱
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
                <span>图谱信息</span>
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
              
              <el-form-item label="图谱名称" prop="name">
                <el-input
                  v-model="form.name"
                  placeholder="请输入图谱名称"
                  clearable
                  show-word-limit
                  maxlength="100"
                />
              </el-form-item>
              
              <el-form-item label="图谱描述" prop="description">
                <el-input
                  v-model="form.description"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入图谱描述"
                  show-word-limit
                  maxlength="1000"
                />
              </el-form-item>
              
              <el-form-item label="图谱类型" prop="type">
                <el-select
                  v-model="form.type"
                  placeholder="选择图谱类型"
                  style="width: 100%"
                >
                  <el-option
                    v-for="type in graphTypes"
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
              
              <el-form-item label="所属领域">
                <el-cascader
                  v-model="form.domain"
                  :options="domainOptions"
                  :props="{ expandTrigger: 'hover', multiple: true }"
                  placeholder="选择所属领域"
                  style="width: 100%"
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                />
              </el-form-item>
              
              <!-- 配置信息 -->
              <div class="form-section-title">
                <el-icon><Setting /></el-icon>
                配置信息
              </div>
              
              <el-form-item label="访问权限">
                <el-radio-group v-model="form.visibility">
                  <el-radio label="public">
                    <el-icon><Unlock /></el-icon>
                    公开
                  </el-radio>
                  <el-radio label="private">
                    <el-icon><Lock /></el-icon>
                    私有
                  </el-radio>
                  <el-radio label="team">
                    <el-icon><UserFilled /></el-icon>
                    团队
                  </el-radio>
                </el-radio-group>
              </el-form-item>
              
              <el-form-item label="版本控制">
                <el-switch
                  v-model="form.versionControl"
                  active-text="启用"
                  inactive-text="禁用"
                />
                <span class="form-tip">启用后可以追踪图谱的历史变更</span>
              </el-form-item>
              
              <el-form-item label="自动备份">
                <el-switch
                  v-model="form.autoBackup"
                  active-text="启用"
                  inactive-text="禁用"
                />
                <span class="form-tip">定期自动备份图谱数据</span>
              </el-form-item>
              
              <el-form-item label="最大节点数">
                <el-input-number
                  v-model="form.maxNodes"
                  :min="100"
                  :max="100000"
                  :step="100"
                  style="width: 200px"
                />
                <span class="form-tip">图谱中允许的最大节点数量</span>
              </el-form-item>
              
              <!-- 初始化选项 -->
              <div class="form-section-title">
                <el-icon><Magic /></el-icon>
                初始化选项
              </div>
              
              <el-form-item label="创建方式">
                <el-radio-group v-model="form.initMethod">
                  <el-radio label="empty">空白图谱</el-radio>
                  <el-radio label="template">使用模板</el-radio>
                  <el-radio label="import">导入数据</el-radio>
                </el-radio-group>
              </el-form-item>
              
              <el-form-item v-if="form.initMethod === 'template'" label="选择模板">
                <el-select
                  v-model="form.templateId"
                  placeholder="选择图谱模板"
                  style="width: 100%"
                >
                  <el-option
                    v-for="template in templates"
                    :key="template.id"
                    :label="template.name"
                    :value="template.id"
                  >
                    <div class="template-option">
                      <div class="template-info">
                        <span class="template-name">{{ template.name }}</span>
                        <el-tag size="small" :type="template.type">
                          {{ template.category }}
                        </el-tag>
                      </div>
                      <span class="template-desc">{{ template.description }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              
              <el-form-item v-if="form.initMethod === 'import'" label="数据文件">
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :show-file-list="true"
                  :limit="1"
                  accept=".json,.csv,.xlsx,.rdf,.owl"
                  @change="handleFileChange"
                >
                  <el-button>
                    <el-icon><Upload /></el-icon>
                    选择文件
                  </el-button>
                  <template #tip>
                    <div class="el-upload__tip">
                      支持 JSON、CSV、Excel、RDF、OWL 格式
                    </div>
                  </template>
                </el-upload>
              </el-form-item>
              
              <!-- 标签和元数据 -->
              <div class="form-section-title">
                <el-icon><Collection /></el-icon>
                标签和元数据
              </div>
              
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
              
              <el-form-item label="关键词">
                <el-input
                  v-model="form.keywords"
                  placeholder="请输入关键词，用逗号分隔"
                  clearable
                />
              </el-form-item>
              
              <!-- 自定义元数据 -->
              <div class="form-section-title">
                <el-icon><Plus /></el-icon>
                自定义元数据
                <el-button size="small" @click="addMetadata">
                  添加元数据
                </el-button>
              </div>
              
              <div v-if="form.metadata.length > 0" class="metadata-list">
                <div
                  v-for="(meta, index) in form.metadata"
                  :key="index"
                  class="metadata-item"
                >
                  <el-input
                    v-model="meta.key"
                    placeholder="键名"
                    style="width: 200px; margin-right: 12px;"
                  />
                  <el-input
                    v-model="meta.value"
                    placeholder="值"
                    style="flex: 1; margin-right: 12px;"
                  />
                  <el-button
                    size="small"
                    @click="removeMetadata(index)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
            </el-form>
          </el-card>
        </el-col>
        
        <!-- 右侧预览 -->
        <el-col :span="8">
          <el-card shadow="never" class="preview-card">
            <template #header>
              <div class="card-header">
                <span>图谱预览</span>
                <el-button text @click="refreshPreview">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </template>
            
            <!-- 图谱卡片预览 -->
            <div class="graph-preview">
              <div class="graph-card">
                <div class="graph-header">
                  <div class="graph-icon">
                    <el-icon :color="getGraphTypeColor(form.type)">
                      <component :is="getGraphTypeIcon(form.type)" />
                    </el-icon>
                  </div>
                  <div class="graph-info">
                    <h3 class="graph-name">{{ form.name || '图谱名称' }}</h3>
                    <el-tag
                      v-if="form.type"
                      size="small"
                      :type="getGraphTypeTagType(form.type)"
                    >
                      {{ getGraphTypeLabel(form.type) }}
                    </el-tag>
                  </div>
                  <div class="graph-status">
                    <el-tag
                      :type="getVisibilityTagType(form.visibility)"
                      size="small"
                    >
                      {{ getVisibilityLabel(form.visibility) }}
                    </el-tag>
                  </div>
                </div>
                
                <div class="graph-description">
                  {{ form.description || '暂无描述' }}
                </div>
                
                <div v-if="form.domain.length > 0" class="graph-domains">
                  <span class="label">领域:</span>
                  <div class="domains-list">
                    <el-tag
                      v-for="domain in flattenDomains"
                      :key="domain"
                      size="small"
                      effect="plain"
                      class="domain-tag"
                    >
                      {{ domain }}
                    </el-tag>
                  </div>
                </div>
                
                <div v-if="form.tags.length > 0" class="graph-tags">
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
              </div>
            </div>
            
            <!-- 配置摘要 -->
            <div class="config-summary">
              <h4>配置摘要</h4>
              <div class="config-item">
                <span class="config-label">最大节点:</span>
                <span class="config-value">{{ form.maxNodes.toLocaleString() }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">版本控制:</span>
                <span class="config-value">{{ form.versionControl ? '启用' : '禁用' }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">自动备份:</span>
                <span class="config-value">{{ form.autoBackup ? '启用' : '禁用' }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">初始化方式:</span>
                <span class="config-value">{{ getInitMethodLabel(form.initMethod) }}</span>
              </div>
            </div>
            
            <!-- 验证结果 -->
            <div class="validation-section">
              <h4>验证结果</h4>
              <div class="validation-item">
                <el-icon :color="validationResults.name ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.name ? 'Check' : 'Close'" />
                </el-icon>
                <span>图谱名称</span>
              </div>
              <div class="validation-item">
                <el-icon :color="validationResults.type ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.type ? 'Check' : 'Close'" />
                </el-icon>
                <span>图谱类型</span>
              </div>
              <div class="validation-item">
                <el-icon :color="validationResults.description ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.description ? 'Check' : 'Close'" />
                </el-icon>
                <span>图谱描述</span>
              </div>
              <div class="validation-item">
                <el-icon :color="validationResults.config ? '#67c23a' : '#f56c6c'">
                  <component :is="validationResults.config ? 'Check' : 'Close'" />
                </el-icon>
                <span>配置信息</span>
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Document,
  Check,
  Refresh,
  Share,
  InfoFilled,
  Setting,
  MagicStick as Magic,
  Collection,
  Plus,
  Delete,
  Close,
  Upload,
  Lock,
  Unlock,
  UserFilled,
  DataBoard,
  Cpu,
  Reading,
  OfficeBuilding,
  Connection
} from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref()
const uploadRef = ref()
const creating = ref(false)

// 表单数据
const form = reactive({
  name: '',
  description: '',
  type: '',
  domain: [],
  visibility: 'private',
  versionControl: true,
  autoBackup: true,
  maxNodes: 10000,
  initMethod: 'empty',
  templateId: '',
  importFile: null,
  tags: [],
  keywords: '',
  metadata: []
})

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入图谱名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择图谱类型', trigger: 'change' }
  ],
  description: [
    { required: true, message: '请输入图谱描述', trigger: 'blur' },
    { min: 10, max: 1000, message: '长度在 10 到 1000 个字符', trigger: 'blur' }
  ]
}

// 图谱类型
const graphTypes = ref([
  {
    value: 'knowledge',
    label: '知识图谱',
    description: '通用知识图谱',
    icon: 'Reading',
    color: '#409eff'
  },
  {
    value: 'business',
    label: '业务图谱',
    description: '业务流程图谱',
    icon: 'OfficeBuilding',
    color: '#67c23a'
  },
  {
    value: 'technical',
    label: '技术图谱',
    description: '技术架构图谱',
    icon: 'Cpu',
    color: '#e6a23c'
  },
  {
    value: 'social',
    label: '社交图谱',
    description: '社交关系图谱',
    icon: 'Connection',
    color: '#f56c6c'
  },
  {
    value: 'data',
    label: '数据图谱',
    description: '数据血缘图谱',
    icon: 'DataBoard',
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
      { value: 'data', label: '数据科学' },
      { value: 'cloud', label: '云计算' }
    ]
  },
  {
    value: 'business',
    label: '商业',
    children: [
      { value: 'finance', label: '金融' },
      { value: 'marketing', label: '市场营销' },
      { value: 'management', label: '管理' },
      { value: 'sales', label: '销售' }
    ]
  },
  {
    value: 'science',
    label: '科学',
    children: [
      { value: 'physics', label: '物理学' },
      { value: 'chemistry', label: '化学' },
      { value: 'biology', label: '生物学' },
      { value: 'medicine', label: '医学' }
    ]
  },
  {
    value: 'education',
    label: '教育',
    children: [
      { value: 'k12', label: '基础教育' },
      { value: 'higher', label: '高等教育' },
      { value: 'vocational', label: '职业教育' }
    ]
  }
])

// 模板数据
const templates = ref([
  {
    id: '1',
    name: '企业知识图谱模板',
    category: '企业',
    type: 'success',
    description: '包含组织架构、业务流程等基础实体'
  },
  {
    id: '2',
    name: '学术研究图谱模板',
    category: '学术',
    type: 'primary',
    description: '包含论文、作者、机构等学术实体'
  },
  {
    id: '3',
    name: '产品知识图谱模板',
    category: '产品',
    type: 'warning',
    description: '包含产品、功能、用户等产品实体'
  }
])

// 可用标签
const availableTags = ref([
  '重要',
  '核心',
  '实验性',
  '生产环境',
  '测试环境',
  '公开',
  '内部',
  '临时'
])

// 计算属性
const flattenDomains = computed(() => {
  return form.domain.map(domainPath => {
    if (Array.isArray(domainPath)) {
      return domainPath.join(' > ')
    }
    return domainPath
  })
})

const validationResults = computed(() => {
  return {
    name: form.name.length >= 2,
    type: !!form.type,
    description: form.description.length >= 10,
    config: form.maxNodes >= 100
  }
})

// 方法
const goBack = () => {
  router.back()
}

const getGraphTypeColor = (type: string) => {
  const typeObj = graphTypes.value.find(t => t.value === type)
  return typeObj?.color || '#909399'
}

const getGraphTypeIcon = (type: string) => {
  const typeObj = graphTypes.value.find(t => t.value === type)
  return typeObj?.icon || 'Share'
}

const getGraphTypeLabel = (type: string) => {
  const typeObj = graphTypes.value.find(t => t.value === type)
  return typeObj?.label || type
}

const getGraphTypeTagType = (type: string) => {
  const types = {
    knowledge: 'primary',
    business: 'success',
    technical: 'warning',
    social: 'danger',
    data: 'info'
  }
  return types[type] || 'info'
}

const getVisibilityTagType = (visibility: string) => {
  const types = {
    public: 'success',
    private: 'danger',
    team: 'warning'
  }
  return types[visibility] || 'info'
}

const getVisibilityLabel = (visibility: string) => {
  const labels = {
    public: '公开',
    private: '私有',
    team: '团队'
  }
  return labels[visibility] || visibility
}

const getInitMethodLabel = (method: string) => {
  const labels = {
    empty: '空白图谱',
    template: '使用模板',
    import: '导入数据'
  }
  return labels[method] || method
}

const addMetadata = () => {
  form.metadata.push({
    key: '',
    value: ''
  })
}

const removeMetadata = (index: number) => {
  form.metadata.splice(index, 1)
}

const handleFileChange = (file: any) => {
  form.importFile = file.raw
}

const resetForm = () => {
  formRef.value?.resetFields()
  form.domain = []
  form.tags = []
  form.metadata = []
  form.visibility = 'private'
  form.versionControl = true
  form.autoBackup = true
  form.maxNodes = 10000
  form.initMethod = 'empty'
  form.templateId = ''
  form.importFile = null
  form.keywords = ''
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

const createGraph = async () => {
  try {
    const valid = await formRef.value?.validate()
    if (!valid) return
    
    creating.value = true
    
    // 这里调用创建图谱的API
    // const response = await graphApi.create({
    //   ...form,
    //   metadata: form.metadata.filter(m => m.key && m.value),
    //   keywords: form.keywords.split(',').map(k => k.trim()).filter(k => k)
    // })
    
    // 模拟创建延迟
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    ElMessage.success('知识图谱创建成功')
    router.push('/knowledge/graphs')
    
  } catch (error) {
    ElMessage.error('创建图谱失败，请重试')
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
.create-graph-page {
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

.template-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.template-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.template-name {
  font-weight: 500;
}

.template-desc {
  font-size: 12px;
  color: #6b7280;
}

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #6b7280;
}

.metadata-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metadata-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.graph-preview {
  margin-bottom: 20px;
}

.graph-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: white;
}

.graph-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.graph-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 8px;
  font-size: 20px;
}

.graph-info {
  flex: 1;
}

.graph-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px 0;
}

.graph-status {
  margin-left: auto;
}

.graph-description {
  color: #6b7280;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 12px;
}

.graph-domains,
.graph-tags {
  margin-bottom: 12px;
}

.label {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  display: block;
  margin-bottom: 4px;
}

.domains-list,
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.domain-tag,
.tag-item {
  margin: 0;
}

.config-summary {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
  margin-bottom: 16px;
}

.config-summary h4 {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 12px 0;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
}

.config-label {
  color: #6b7280;
}

.config-value {
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
  .create-graph-page {
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
  
  .metadata-item {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>