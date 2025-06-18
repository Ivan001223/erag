<template>
  <div class="relation-detail">
    <!-- 页面头部 -->
    <div class="detail-header">
      <div class="header-content">
        <div class="breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/knowledge' }">知识库</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ path: '/knowledge/relations' }">关系管理</el-breadcrumb-item>
            <el-breadcrumb-item>{{ relationData.name || '关系详情' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-actions">
          <el-button @click="$router.go(-1)">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <el-button @click="exportRelation">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
          <el-button type="primary" @click="editRelation">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
      </div>
    </div>

    <!-- 关系基本信息 -->
    <div class="relation-info-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>关系信息</h3>
            <div class="relation-status">
              <el-tag :type="getStatusType(relationData.status)">{{ relationData.status }}</el-tag>
            </div>
          </div>
        </template>
        
        <div class="relation-info">
          <div class="relation-visual">
            <div class="relation-diagram">
              <div class="entity-node source">
                <div class="node-icon">
                  <el-icon><User /></el-icon>
                </div>
                <div class="node-label">{{ relationData.sourceEntity }}</div>
                <div class="node-type">{{ relationData.sourceType }}</div>
              </div>
              
              <div class="relation-arrow">
                <div class="arrow-line"></div>
                <div class="relation-label">
                  <span class="relation-name">{{ relationData.name }}</span>
                  <span class="relation-type">{{ relationData.type }}</span>
                </div>
                <div class="arrow-head"></div>
              </div>
              
              <div class="entity-node target">
                <div class="node-icon">
                  <el-icon><OfficeBuilding /></el-icon>
                </div>
                <div class="node-label">{{ relationData.targetEntity }}</div>
                <div class="node-type">{{ relationData.targetType }}</div>
              </div>
            </div>
          </div>
          
          <div class="relation-details">
            <div class="info-grid">
              <div class="info-item">
                <span class="label">关系名称：</span>
                <span class="value">{{ relationData.name }}</span>
              </div>
              <div class="info-item">
                <span class="label">关系类型：</span>
                <span class="value">{{ relationData.type }}</span>
              </div>
              <div class="info-item">
                <span class="label">方向性：</span>
                <span class="value">{{ relationData.direction ? '有向' : '无向' }}</span>
              </div>
              <div class="info-item">
                <span class="label">权重：</span>
                <span class="value">
                  <el-rate v-model="relationData.weight" disabled show-score text-color="#ff9900" />
                </span>
              </div>
              <div class="info-item">
                <span class="label">置信度：</span>
                <span class="value">{{ (relationData.confidence * 100).toFixed(1) }}%</span>
              </div>
              <div class="info-item">
                <span class="label">创建时间：</span>
                <span class="value">{{ formatDate(relationData.createTime) }}</span>
              </div>
              <div class="info-item">
                <span class="label">更新时间：</span>
                <span class="value">{{ formatDate(relationData.updateTime) }}</span>
              </div>
              <div class="info-item">
                <span class="label">创建者：</span>
                <span class="value">{{ relationData.creator }}</span>
              </div>
            </div>
            
            <div class="relation-description" v-if="relationData.description">
              <h4>描述</h4>
              <p>{{ relationData.description }}</p>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 关系属性 -->
    <div class="relation-properties-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>关系属性</h3>
            <el-button size="small" @click="addProperty">
              <el-icon><Plus /></el-icon>
              添加属性
            </el-button>
          </div>
        </template>
        
        <div class="properties-content" v-loading="propertiesLoading">
          <el-table :data="relationData.properties" stripe>
            <el-table-column prop="name" label="属性名" min-width="120" />
            <el-table-column prop="value" label="属性值" min-width="150">
              <template #default="{ row }">
                <span v-if="row.type === 'text'">{{ row.value }}</span>
                <el-tag v-else-if="row.type === 'tag'" size="small">{{ row.value }}</el-tag>
                <span v-else-if="row.type === 'number'">{{ row.value }}</span>
                <span v-else-if="row.type === 'date'">{{ formatDate(row.value) }}</span>
                <el-switch v-else-if="row.type === 'boolean'" v-model="row.value" disabled />
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="updateTime" label="更新时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.updateTime) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row, $index }">
                <el-button size="small" text @click="editProperty(row, $index)">
                  编辑
                </el-button>
                <el-button size="small" text type="danger" @click="deleteProperty($index)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div v-if="!relationData.properties?.length" class="empty-state">
            <el-empty description="暂无属性数据" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 相关实体 -->
    <div class="related-entities-section">
      <el-card>
        <template #header>
          <h3>相关实体</h3>
        </template>
        
        <div class="entities-content">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="entity-card source-entity">
                <div class="entity-header">
                  <h4>源实体</h4>
                  <el-button size="small" text @click="viewEntity(relationData.sourceEntityId)">
                    查看详情
                  </el-button>
                </div>
                
                <div class="entity-info">
                  <div class="entity-avatar">
                    <el-icon><User /></el-icon>
                  </div>
                  <div class="entity-details">
                    <div class="entity-name">{{ relationData.sourceEntity }}</div>
                    <div class="entity-type">{{ relationData.sourceType }}</div>
                    <div class="entity-description">{{ relationData.sourceDescription }}</div>
                  </div>
                </div>
                
                <div class="entity-stats">
                  <div class="stat-item">
                    <span class="stat-label">关系数：</span>
                    <span class="stat-value">{{ relationData.sourceRelationCount }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">创建时间：</span>
                    <span class="stat-value">{{ formatDate(relationData.sourceCreateTime) }}</span>
                  </div>
                </div>
              </div>
            </el-col>
            
            <el-col :span="12">
              <div class="entity-card target-entity">
                <div class="entity-header">
                  <h4>目标实体</h4>
                  <el-button size="small" text @click="viewEntity(relationData.targetEntityId)">
                    查看详情
                  </el-button>
                </div>
                
                <div class="entity-info">
                  <div class="entity-avatar">
                    <el-icon><OfficeBuilding /></el-icon>
                  </div>
                  <div class="entity-details">
                    <div class="entity-name">{{ relationData.targetEntity }}</div>
                    <div class="entity-type">{{ relationData.targetType }}</div>
                    <div class="entity-description">{{ relationData.targetDescription }}</div>
                  </div>
                </div>
                
                <div class="entity-stats">
                  <div class="stat-item">
                    <span class="stat-label">关系数：</span>
                    <span class="stat-value">{{ relationData.targetRelationCount }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">创建时间：</span>
                    <span class="stat-value">{{ formatDate(relationData.targetCreateTime) }}</span>
                  </div>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-card>
    </div>

    <!-- 证据来源 -->
    <div class="evidence-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>证据来源</h3>
            <el-button size="small" @click="addEvidence">
              <el-icon><Plus /></el-icon>
              添加证据
            </el-button>
          </div>
        </template>
        
        <div class="evidence-content" v-loading="evidenceLoading">
          <div class="evidence-list">
            <div v-for="(evidence, index) in relationData.evidences" :key="index" class="evidence-item">
              <div class="evidence-header">
                <div class="evidence-type">
                  <el-icon><Document /></el-icon>
                  <span>{{ evidence.type }}</span>
                </div>
                <div class="evidence-actions">
                  <el-button size="small" text @click="viewEvidence(evidence)">
                    查看
                  </el-button>
                  <el-button size="small" text type="danger" @click="deleteEvidence(index)">
                    删除
                  </el-button>
                </div>
              </div>
              
              <div class="evidence-content-text">
                <p>{{ evidence.content }}</p>
              </div>
              
              <div class="evidence-meta">
                <span class="evidence-source">来源：{{ evidence.source }}</span>
                <span class="evidence-confidence">置信度：{{ (evidence.confidence * 100).toFixed(1) }}%</span>
                <span class="evidence-time">时间：{{ formatDate(evidence.createTime) }}</span>
              </div>
            </div>
          </div>
          
          <div v-if="!relationData.evidences?.length" class="empty-state">
            <el-empty description="暂无证据数据" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 操作历史 -->
    <div class="history-section">
      <el-card>
        <template #header>
          <h3>操作历史</h3>
        </template>
        
        <div class="history-content" v-loading="historyLoading">
          <el-timeline>
            <el-timeline-item
              v-for="(item, index) in operationHistory"
              :key="index"
              :timestamp="formatDate(item.timestamp)"
              :type="getTimelineType(item.type)"
            >
              <div class="history-item">
                <div class="history-header">
                  <span class="history-action">{{ item.action }}</span>
                  <span class="history-user">{{ item.user }}</span>
                </div>
                <div class="history-description">{{ item.description }}</div>
                <div class="history-details" v-if="item.details">
                  <el-tag size="small" v-for="detail in item.details" :key="detail">{{ detail }}</el-tag>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
          
          <div v-if="!operationHistory?.length" class="empty-state">
            <el-empty description="暂无操作历史" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑关系" width="600px">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="100px">
        <el-form-item label="关系名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入关系名称" />
        </el-form-item>
        <el-form-item label="关系类型" prop="type">
          <el-select v-model="editForm.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="属于" value="belongs_to" />
            <el-option label="包含" value="contains" />
            <el-option label="关联" value="related_to" />
            <el-option label="依赖" value="depends_on" />
            <el-option label="影响" value="affects" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="方向性">
          <el-switch v-model="editForm.direction" active-text="有向" inactive-text="无向" />
        </el-form-item>
        <el-form-item label="权重">
          <el-rate v-model="editForm.weight" show-score text-color="#ff9900" />
        </el-form-item>
        <el-form-item label="置信度">
          <el-slider v-model="editForm.confidence" :min="0" :max="100" :step="1" show-input />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveRelation" :loading="saving">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 属性编辑对话框 -->
    <el-dialog v-model="propertyDialogVisible" title="编辑属性" width="500px">
      <el-form :model="propertyForm" :rules="propertyRules" ref="propertyFormRef" label-width="80px">
        <el-form-item label="属性名" prop="name">
          <el-input v-model="propertyForm.name" placeholder="请输入属性名" />
        </el-form-item>
        <el-form-item label="属性值" prop="value">
          <el-input v-model="propertyForm.value" placeholder="请输入属性值" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="propertyForm.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="文本" value="text" />
            <el-option label="数字" value="number" />
            <el-option label="日期" value="date" />
            <el-option label="布尔" value="boolean" />
            <el-option label="标签" value="tag" />
          </el-select>
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
  Download,
  Edit,
  User,
  OfficeBuilding,
  Plus,
  Document
} from '@element-plus/icons-vue'

interface RelationData {
  id: string
  name: string
  type: string
  status: string
  direction: boolean
  weight: number
  confidence: number
  description: string
  createTime: string
  updateTime: string
  creator: string
  sourceEntity: string
  sourceEntityId: string
  sourceType: string
  sourceDescription: string
  sourceRelationCount: number
  sourceCreateTime: string
  targetEntity: string
  targetEntityId: string
  targetType: string
  targetDescription: string
  targetRelationCount: number
  targetCreateTime: string
  properties: Array<{
    name: string
    value: any
    type: string
    updateTime: string
  }>
  evidences: Array<{
    type: string
    content: string
    source: string
    confidence: number
    createTime: string
  }>
}

interface OperationHistory {
  action: string
  user: string
  description: string
  timestamp: string
  type: string
  details?: string[]
}

const route = useRoute()
const router = useRouter()

const relationId = route.params.id as string

const loading = ref(false)
const propertiesLoading = ref(false)
const evidenceLoading = ref(false)
const historyLoading = ref(false)
const saving = ref(false)

const editDialogVisible = ref(false)
const propertyDialogVisible = ref(false)

const editFormRef = ref()
const propertyFormRef = ref()

const currentPropertyIndex = ref(-1)

const relationData = ref<RelationData>({
  id: '',
  name: '',
  type: '',
  status: '',
  direction: true,
  weight: 0,
  confidence: 0,
  description: '',
  createTime: '',
  updateTime: '',
  creator: '',
  sourceEntity: '',
  sourceEntityId: '',
  sourceType: '',
  sourceDescription: '',
  sourceRelationCount: 0,
  sourceCreateTime: '',
  targetEntity: '',
  targetEntityId: '',
  targetType: '',
  targetDescription: '',
  targetRelationCount: 0,
  targetCreateTime: '',
  properties: [],
  evidences: []
})

const operationHistory = ref<OperationHistory[]>([])

const editForm = reactive({
  name: '',
  type: '',
  direction: true,
  weight: 0,
  confidence: 0,
  description: ''
})

const propertyForm = reactive({
  name: '',
  value: '',
  type: 'text'
})

const editRules = {
  name: [
    { required: true, message: '请输入关系名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择关系类型', trigger: 'change' }
  ]
}

const propertyRules = {
  name: [
    { required: true, message: '请输入属性名', trigger: 'blur' }
  ],
  value: [
    { required: true, message: '请输入属性值', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择类型', trigger: 'change' }
  ]
}

// 获取状态类型
const getStatusType = (status: string): string => {
  const typeMap: Record<string, string> = {
    'active': 'success',
    'inactive': 'warning',
    'pending': 'info',
    'error': 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取时间线类型
const getTimelineType = (type: string): string => {
  const typeMap: Record<string, string> = {
    'create': 'primary',
    'update': 'success',
    'delete': 'danger',
    'view': 'info'
  }
  return typeMap[type] || 'info'
}

// 格式化日期
const formatDate = (dateString: string): string => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN')
}

// 导出关系
const exportRelation = () => {
  ElMessage.success('开始导出关系数据')
}

// 编辑关系
const editRelation = () => {
  Object.assign(editForm, {
    name: relationData.value.name,
    type: relationData.value.type,
    direction: relationData.value.direction,
    weight: relationData.value.weight,
    confidence: relationData.value.confidence * 100,
    description: relationData.value.description
  })
  editDialogVisible.value = true
}

// 保存关系
const saveRelation = async () => {
  if (!editFormRef.value) return
  
  try {
    await editFormRef.value.validate()
    
    saving.value = true
    
    // 这里应该调用实际的API
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    Object.assign(relationData.value, {
      ...editForm,
      confidence: editForm.confidence / 100
    })
    
    ElMessage.success('保存成功')
    editDialogVisible.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 查看实体
const viewEntity = (entityId: string) => {
  router.push(`/knowledge/entities/detail/${entityId}`)
}

// 添加属性
const addProperty = () => {
  Object.assign(propertyForm, {
    name: '',
    value: '',
    type: 'text'
  })
  currentPropertyIndex.value = -1
  propertyDialogVisible.value = true
}

// 编辑属性
const editProperty = (property: any, index: number) => {
  Object.assign(propertyForm, property)
  currentPropertyIndex.value = index
  propertyDialogVisible.value = true
}

// 保存属性
const saveProperty = async () => {
  if (!propertyFormRef.value) return
  
  try {
    await propertyFormRef.value.validate()
    
    saving.value = true
    
    // 这里应该调用实际的API
    await new Promise(resolve => setTimeout(resolve, 500))
    
    const newProperty = {
      ...propertyForm,
      updateTime: new Date().toISOString()
    }
    
    if (currentPropertyIndex.value >= 0) {
      relationData.value.properties[currentPropertyIndex.value] = newProperty
    } else {
      relationData.value.properties.push(newProperty)
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
const deleteProperty = async (index: number) => {
  try {
    await ElMessageBox.confirm('确定要删除这个属性吗？', '确认删除', {
      type: 'warning'
    })
    
    relationData.value.properties.splice(index, 1)
    ElMessage.success('删除成功')
  } catch (error) {
    // 用户取消删除
  }
}

// 添加证据
const addEvidence = () => {
  ElMessage.info('添加证据功能')
}

// 查看证据
const viewEvidence = (evidence: any) => {
  ElMessage.info(`查看证据: ${evidence.type}`)
}

// 删除证据
const deleteEvidence = async (index: number) => {
  try {
    await ElMessageBox.confirm('确定要删除这个证据吗？', '确认删除', {
      type: 'warning'
    })
    
    relationData.value.evidences.splice(index, 1)
    ElMessage.success('删除成功')
  } catch (error) {
    // 用户取消删除
  }
}

// 获取关系详情
const fetchRelationDetail = async () => {
  try {
    loading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    relationData.value = {
      id: relationId,
      name: '工作于',
      type: 'belongs_to',
      status: 'active',
      direction: true,
      weight: 4,
      confidence: 0.85,
      description: '表示人员与组织之间的工作关系',
      createTime: '2024-01-15T10:30:00Z',
      updateTime: '2024-01-20T14:20:00Z',
      creator: '管理员',
      sourceEntity: '张三',
      sourceEntityId: '1',
      sourceType: '人员',
      sourceDescription: '技术部高级工程师',
      sourceRelationCount: 8,
      sourceCreateTime: '2024-01-10T10:30:00Z',
      targetEntity: '技术部',
      targetEntityId: '2',
      targetType: '部门',
      targetDescription: '负责公司技术研发工作',
      targetRelationCount: 25,
      targetCreateTime: '2024-01-01T10:30:00Z',
      properties: [
        {
          name: '职位',
          value: '高级工程师',
          type: 'text',
          updateTime: '2024-01-15T10:30:00Z'
        },
        {
          name: '入职时间',
          value: '2024-01-10T10:30:00Z',
          type: 'date',
          updateTime: '2024-01-15T10:30:00Z'
        },
        {
          name: '是否在职',
          value: true,
          type: 'boolean',
          updateTime: '2024-01-15T10:30:00Z'
        }
      ],
      evidences: [
        {
          type: '人事档案',
          content: '根据人事档案记录，张三于2024年1月10日入职技术部，担任高级工程师职位。',
          source: '人事管理系统',
          confidence: 0.95,
          createTime: '2024-01-15T10:30:00Z'
        },
        {
          type: '组织架构图',
          content: '在最新的组织架构图中，张三被标记为技术部成员。',
          source: '组织管理系统',
          confidence: 0.90,
          createTime: '2024-01-16T10:30:00Z'
        }
      ]
    }
  } catch (error) {
    ElMessage.error('获取关系详情失败')
  } finally {
    loading.value = false
  }
}

// 获取操作历史
const fetchOperationHistory = async () => {
  try {
    historyLoading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    operationHistory.value = [
      {
        action: '创建关系',
        user: '管理员',
        description: '创建了张三与技术部的工作关系',
        timestamp: '2024-01-15T10:30:00Z',
        type: 'create',
        details: ['关系类型: 工作于', '权重: 4', '置信度: 85%']
      },
      {
        action: '更新属性',
        user: '管理员',
        description: '更新了职位信息',
        timestamp: '2024-01-16T14:20:00Z',
        type: 'update',
        details: ['职位: 高级工程师']
      },
      {
        action: '添加证据',
        user: '系统管理员',
        description: '添加了人事档案证据',
        timestamp: '2024-01-17T09:15:00Z',
        type: 'create',
        details: ['证据类型: 人事档案', '置信度: 95%']
      },
      {
        action: '查看详情',
        user: '张三',
        description: '查看了关系详情',
        timestamp: '2024-01-20T16:45:00Z',
        type: 'view'
      }
    ]
  } catch (error) {
    ElMessage.error('获取操作历史失败')
  } finally {
    historyLoading.value = false
  }
}

onMounted(() => {
  fetchRelationDetail()
  fetchOperationHistory()
})
</script>

<style scoped>
.relation-detail {
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

.relation-info-section,
.relation-properties-section,
.related-entities-section,
.evidence-section,
.history-section {
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

.relation-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

.relation-visual {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.relation-diagram {
  display: flex;
  align-items: center;
  gap: 40px;
}

.entity-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  background-color: #f8f9fa;
  min-width: 120px;
}

.entity-node.source {
  border-color: #409eff;
}

.entity-node.target {
  border-color: #67c23a;
}

.node-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #409eff;
  color: #fff;
  border-radius: 50%;
  font-size: 20px;
  margin-bottom: 8px;
}

.target .node-icon {
  background-color: #67c23a;
}

.node-label {
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.node-type {
  font-size: 12px;
  color: #909399;
}

.relation-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.arrow-line {
  width: 60px;
  height: 2px;
  background-color: #409eff;
  position: relative;
}

.arrow-head {
  width: 0;
  height: 0;
  border-left: 8px solid #409eff;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  position: absolute;
  right: -8px;
  top: 50%;
  transform: translateY(-50%);
}

.relation-label {
  position: absolute;
  top: -30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  white-space: nowrap;
}

.relation-name {
  font-weight: bold;
  color: #303133;
  font-size: 14px;
}

.relation-type {
  font-size: 12px;
  color: #909399;
}

.relation-details {
  padding-left: 24px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-item .label {
  color: #909399;
  margin-right: 8px;
  min-width: 80px;
}

.info-item .value {
  color: #303133;
  font-weight: 500;
}

.relation-description h4 {
  margin: 0 0 8px 0;
  color: #303133;
}

.relation-description p {
  color: #606266;
  line-height: 1.6;
  margin: 0;
}

.properties-content,
.evidence-content,
.history-content {
  min-height: 200px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.entity-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  background-color: #fafafa;
}

.entity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.entity-header h4 {
  margin: 0;
  color: #303133;
}

.entity-info {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.entity-avatar {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #409eff;
  color: #fff;
  border-radius: 50%;
  font-size: 24px;
}

.entity-details {
  flex: 1;
}

.entity-name {
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.entity-type {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.entity-description {
  font-size: 14px;
  color: #606266;
  line-height: 1.4;
}

.entity-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.stat-label {
  color: #909399;
}

.stat-value {
  color: #303133;
  font-weight: 500;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.evidence-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  background-color: #fafafa;
}

.evidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.evidence-type {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  color: #303133;
}

.evidence-actions {
  display: flex;
  gap: 8px;
}

.evidence-content-text {
  margin-bottom: 12px;
}

.evidence-content-text p {
  color: #606266;
  line-height: 1.6;
  margin: 0;
}

.evidence-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.history-item {
  padding: 8px 0;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.history-action {
  font-weight: bold;
  color: #303133;
}

.history-user {
  color: #909399;
  font-size: 14px;
}

.history-description {
  color: #606266;
  margin-bottom: 8px;
}

.history-details {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .relation-detail {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .relation-info {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .relation-diagram {
    flex-direction: column;
    gap: 20px;
  }
  
  .relation-arrow {
    transform: rotate(90deg);
  }
  
  .relation-label {
    transform: rotate(-90deg);
  }
  
  .relation-details {
    padding-left: 0;
  }
  
  .evidence-meta {
    flex-direction: column;
    gap: 4px;
  }
}
</style>