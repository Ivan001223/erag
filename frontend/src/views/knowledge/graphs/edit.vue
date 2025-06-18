<template>
  <div class="graph-edit-container">
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
          <h2>{{ isEdit ? '编辑知识图谱' : '查看知识图谱' }}</h2>
          <span class="subtitle">{{ graphData.name || '未命名图谱' }}</span>
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

    <!-- 图谱信息 -->
    <div class="graph-info-section">
      <el-card>
        <template #header>
          <span>基本信息</span>
        </template>
        <el-form 
          ref="formRef"
          :model="graphData" 
          :rules="formRules"
          label-width="120px"
          :disabled="!isEdit"
        >
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="图谱名称" prop="name">
                <el-input v-model="graphData.name" placeholder="请输入图谱名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="图谱类型" prop="type">
                <el-select v-model="graphData.type" placeholder="请选择图谱类型">
                  <el-option label="知识图谱" value="knowledge" />
                  <el-option label="关系图谱" value="relation" />
                  <el-option label="概念图谱" value="concept" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="状态" prop="status">
                <el-select v-model="graphData.status" placeholder="请选择状态">
                  <el-option label="活跃" value="active" />
                  <el-option label="草稿" value="draft" />
                  <el-option label="已归档" value="archived" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="可见性" prop="visibility">
                <el-select v-model="graphData.visibility" placeholder="请选择可见性">
                  <el-option label="公开" value="public" />
                  <el-option label="私有" value="private" />
                  <el-option label="团队" value="team" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="描述" prop="description">
            <el-input 
              v-model="graphData.description" 
              type="textarea" 
              :rows="4"
              placeholder="请输入图谱描述"
            />
          </el-form-item>
          <el-form-item label="标签" prop="tags">
            <el-tag
              v-for="tag in graphData.tags"
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
    </div>

    <!-- 统计信息 -->
    <div class="stats-section">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ graphData.entityCount || 0 }}</div>
              <div class="stat-label">实体数量</div>
            </div>
            <el-icon class="stat-icon"><Grid /></el-icon>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ graphData.relationCount || 0 }}</div>
              <div class="stat-label">关系数量</div>
            </div>
            <el-icon class="stat-icon"><Share /></el-icon>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ graphData.nodeCount || 0 }}</div>
              <div class="stat-label">节点数量</div>
            </div>
            <el-icon class="stat-icon"><Connection /></el-icon>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ graphData.edgeCount || 0 }}</div>
              <div class="stat-label">边数量</div>
            </div>
            <el-icon class="stat-icon"><Promotion /></el-icon>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 图谱可视化 -->
    <div class="visualization-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>图谱可视化</span>
            <div class="header-actions">
              <el-button size="small" @click="refreshVisualization">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button size="small" @click="exportGraph">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </div>
          </div>
        </template>
        <div class="visualization-container" ref="visualizationRef">
          <!-- 这里将集成图谱可视化组件 -->
          <div class="placeholder">
            <el-icon size="64"><PictureRounded /></el-icon>
            <p>图谱可视化组件</p>
          </div>
        </div>
      </el-card>
    </div>
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
  Grid,
  Share,
  Connection,
  Promotion,
  Refresh,
  Download,
  PictureRounded
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 表单引用
const formRef = ref<FormInstance>()
const visualizationRef = ref<HTMLElement>()
const inputRef = ref<HTMLInputElement>()

// 状态
const isEdit = ref(false)
const saving = ref(false)
const inputVisible = ref(false)
const inputValue = ref('')

// 图谱数据
const graphData = reactive({
  id: '',
  name: '',
  type: 'knowledge',
  status: 'active',
  visibility: 'private',
  description: '',
  tags: [] as string[],
  entityCount: 0,
  relationCount: 0,
  nodeCount: 0,
  edgeCount: 0,
  createdAt: '',
  updatedAt: ''
})

// 原始数据备份
const originalData = ref({})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入图谱名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择图谱类型', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

// 加载图谱数据
const loadGraphData = async () => {
  try {
    const graphId = route.params.id as string
    // 模拟API调用
    const mockData = {
      id: graphId,
      name: '示例知识图谱',
      type: 'knowledge',
      status: 'active',
      visibility: 'private',
      description: '这是一个示例知识图谱，用于演示图谱编辑功能。',
      tags: ['AI', '知识管理', '图谱'],
      entityCount: 156,
      relationCount: 234,
      nodeCount: 156,
      edgeCount: 234,
      createdAt: '2024-01-15 10:30:00',
      updatedAt: '2024-01-20 16:45:00'
    }
    
    Object.assign(graphData, mockData)
    originalData.value = JSON.parse(JSON.stringify(mockData))
  } catch (error) {
    ElMessage.error('加载图谱数据失败')
    console.error('Load graph data error:', error)
  }
}

// 保存图谱
const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    saving.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    originalData.value = JSON.parse(JSON.stringify(graphData))
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
  const hasChanges = JSON.stringify(graphData) !== JSON.stringify(originalData.value)
  
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
      
      Object.assign(graphData, originalData.value)
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
  const index = graphData.tags.indexOf(tag)
  if (index > -1) {
    graphData.tags.splice(index, 1)
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
  if (inputValue.value && !graphData.tags.includes(inputValue.value)) {
    graphData.tags.push(inputValue.value)
  }
  inputVisible.value = false
  inputValue.value = ''
}

// 刷新可视化
const refreshVisualization = () => {
  ElMessage.info('刷新图谱可视化')
}

// 导出图谱
const exportGraph = () => {
  ElMessage.info('导出图谱功能开发中')
}

// 组件挂载
onMounted(() => {
  loadGraphData()
})
</script>

<style scoped>
.graph-edit-container {
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

.graph-info-section {
  margin-bottom: 20px;
}

.stats-section {
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  overflow: hidden;
}

.stat-card :deep(.el-card__body) {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.stat-icon {
  font-size: 32px;
  color: #e6f7ff;
  opacity: 0.8;
}

.visualization-section {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.visualization-container {
  height: 500px;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.placeholder {
  text-align: center;
}

.placeholder p {
  margin: 8px 0 0 0;
  font-size: 14px;
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
</style>