<template>
  <div class="document-upload">
    <!-- 页面头部 -->
    <div class="upload-header">
      <div class="header-content">
        <div class="breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/knowledge' }">知识库</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ path: '/knowledge/documents' }">文档管理</el-breadcrumb-item>
            <el-breadcrumb-item>文档上传</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-actions">
          <el-button @click="$router.go(-1)">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
        </div>
      </div>
    </div>

    <!-- 上传区域 -->
    <div class="upload-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>文档上传</h3>
            <div class="upload-tips">
              <el-icon><InfoFilled /></el-icon>
              <span>支持 PDF、Word、Excel、PowerPoint、图片等格式，单个文件最大 100MB</span>
            </div>
          </div>
        </template>
        
        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            class="upload-dragger"
            drag
            :action="uploadUrl"
            :headers="uploadHeaders"
            :data="uploadData"
            :before-upload="beforeUpload"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :on-progress="handleUploadProgress"
            :on-remove="handleRemove"
            :file-list="fileList"
            :auto-upload="false"
            multiple
          >
            <div class="upload-content">
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">
                <p class="primary-text">将文件拖拽到此处，或<em>点击上传</em></p>
                <p class="secondary-text">支持批量上传，建议单个文件不超过 100MB</p>
              </div>
            </div>
          </el-upload>
        </div>
      </el-card>
    </div>

    <!-- 文件列表 -->
    <div class="file-list-section" v-if="fileList.length > 0">
      <el-card>
        <template #header>
          <div class="list-header">
            <h3>待上传文件 ({{ fileList.length }})</h3>
            <div class="list-actions">
              <el-button size="small" @click="clearAll">清空列表</el-button>
              <el-button type="primary" size="small" @click="startUpload" :loading="uploading">
                开始上传
              </el-button>
            </div>
          </div>
        </template>
        
        <div class="file-list">
          <div v-for="(file, index) in fileList" :key="file.uid" class="file-item">
            <div class="file-info">
              <div class="file-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="file-details">
                <div class="file-name">{{ file.name }}</div>
                <div class="file-meta">
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  <span class="file-type">{{ getFileType(file.name) }}</span>
                </div>
              </div>
            </div>
            
            <div class="file-status">
              <div v-if="file.status === 'uploading'" class="upload-progress">
                <el-progress :percentage="file.percentage" :show-text="false" />
                <span class="progress-text">{{ file.percentage }}%</span>
              </div>
              <div v-else-if="file.status === 'success'" class="upload-success">
                <el-icon color="#67c23a"><CircleCheck /></el-icon>
                <span>上传成功</span>
              </div>
              <div v-else-if="file.status === 'fail'" class="upload-error">
                <el-icon color="#f56c6c"><CircleClose /></el-icon>
                <span>上传失败</span>
              </div>
              <div v-else class="upload-ready">
                <span>等待上传</span>
              </div>
            </div>
            
            <div class="file-actions">
              <el-button size="small" text @click="removeFile(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 文档信息表单 -->
    <div class="document-form-section" v-if="showDocumentForm">
      <el-card>
        <template #header>
          <h3>文档信息</h3>
        </template>
        
        <el-form :model="documentForm" :rules="formRules" ref="formRef" label-width="100px">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="文档标题" prop="title">
                <el-input v-model="documentForm.title" placeholder="请输入文档标题" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="文档分类" prop="category">
                <el-select v-model="documentForm.category" placeholder="请选择分类" style="width: 100%">
                  <el-option label="技术文档" value="tech" />
                  <el-option label="产品文档" value="product" />
                  <el-option label="管理制度" value="management" />
                  <el-option label="培训资料" value="training" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="访问权限" prop="permission">
                <el-select v-model="documentForm.permission" placeholder="请选择权限" style="width: 100%">
                  <el-option label="公开" value="public" />
                  <el-option label="内部" value="internal" />
                  <el-option label="私有" value="private" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="优先级" prop="priority">
                <el-select v-model="documentForm.priority" placeholder="请选择优先级" style="width: 100%">
                  <el-option label="高" value="high" />
                  <el-option label="中" value="medium" />
                  <el-option label="低" value="low" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item label="标签">
            <el-select
              v-model="documentForm.tags"
              multiple
              filterable
              allow-create
              placeholder="请选择或输入标签"
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
          
          <el-form-item label="描述">
            <el-input
              v-model="documentForm.description"
              type="textarea"
              :rows="4"
              placeholder="请输入文档描述"
            />
          </el-form-item>
          
          <el-form-item label="处理选项">
            <el-checkbox-group v-model="documentForm.processOptions">
              <el-checkbox label="ocr">启用 OCR 文字识别</el-checkbox>
              <el-checkbox label="extract">自动提取关键信息</el-checkbox>
              <el-checkbox label="index">建立搜索索引</el-checkbox>
              <el-checkbox label="knowledge">加入知识图谱</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 上传历史 -->
    <div class="upload-history-section">
      <el-card>
        <template #header>
          <div class="history-header">
            <h3>最近上传</h3>
            <el-button size="small" text @click="refreshHistory">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        
        <div class="history-list" v-loading="historyLoading">
          <div v-for="item in uploadHistory" :key="item.id" class="history-item">
            <div class="history-info">
              <div class="history-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="history-details">
                <div class="history-name">{{ item.name }}</div>
                <div class="history-meta">
                  <span>{{ formatDate(item.uploadTime) }}</span>
                  <span>{{ formatFileSize(item.size) }}</span>
                </div>
              </div>
            </div>
            
            <div class="history-status">
              <el-tag :type="getStatusType(item.status)">{{ item.status }}</el-tag>
            </div>
            
            <div class="history-actions">
              <el-button size="small" text @click="viewDocument(item.id)">
                查看
              </el-button>
              <el-button size="small" text @click="downloadDocument(item.id)">
                下载
              </el-button>
            </div>
          </div>
          
          <div v-if="uploadHistory.length === 0" class="empty-history">
            <el-empty description="暂无上传记录" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 底部操作栏 -->
    <div class="bottom-actions" v-if="fileList.length > 0">
      <div class="actions-content">
        <div class="upload-summary">
          <span>共 {{ fileList.length }} 个文件，总大小 {{ getTotalSize() }}</span>
        </div>
        <div class="actions-buttons">
          <el-button @click="clearAll">清空</el-button>
          <el-button type="primary" @click="submitUpload" :loading="uploading">
            确认上传
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadInstance, UploadProps, UploadRawFile } from 'element-plus'
import {
  ArrowLeft,
  InfoFilled,
  UploadFilled,
  Document,
  CircleCheck,
  CircleClose,
  Delete,
  Refresh
} from '@element-plus/icons-vue'

interface FileItem {
  uid: number
  name: string
  size: number
  status: string
  percentage?: number
  raw?: File
}

interface HistoryItem {
  id: string
  name: string
  size: number
  uploadTime: string
  status: string
}

const router = useRouter()
const uploadRef = ref<UploadInstance>()
const formRef = ref()

const uploading = ref(false)
const historyLoading = ref(false)
const fileList = ref<FileItem[]>([])
const uploadHistory = ref<HistoryItem[]>([])

const showDocumentForm = computed(() => fileList.value.length > 0)

const documentForm = reactive({
  title: '',
  category: '',
  permission: 'internal',
  priority: 'medium',
  tags: [] as string[],
  description: '',
  processOptions: ['index'] as string[]
})

const formRules = {
  title: [
    { required: true, message: '请输入文档标题', trigger: 'blur' }
  ],
  category: [
    { required: true, message: '请选择文档分类', trigger: 'change' }
  ],
  permission: [
    { required: true, message: '请选择访问权限', trigger: 'change' }
  ]
}

const availableTags = ref([
  '技术文档', '产品说明', '用户手册', '开发指南',
  '设计规范', '测试报告', '项目文档', '培训资料'
])

const uploadUrl = '/api/v1/documents/upload'
const uploadHeaders = {
  'Authorization': 'Bearer ' + localStorage.getItem('token')
}
const uploadData = {
  type: 'document'
}

// 文件上传前检查
const beforeUpload: UploadProps['beforeUpload'] = (rawFile) => {
  const allowedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/jpeg',
    'image/png',
    'image/gif',
    'text/plain'
  ]
  
  if (!allowedTypes.includes(rawFile.type)) {
    ElMessage.error('不支持的文件格式')
    return false
  }
  
  if (rawFile.size > 100 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }
  
  return true
}

// 上传成功
const handleUploadSuccess = (response: any, file: any) => {
  ElMessage.success(`${file.name} 上传成功`)
  refreshHistory()
}

// 上传失败
const handleUploadError = (error: any, file: any) => {
  ElMessage.error(`${file.name} 上传失败`)
}

// 上传进度
const handleUploadProgress = (event: any, file: any) => {
  // 进度更新逻辑
}

// 移除文件
const handleRemove = (file: any) => {
  const index = fileList.value.findIndex(item => item.uid === file.uid)
  if (index > -1) {
    fileList.value.splice(index, 1)
  }
}

// 移除指定文件
const removeFile = (index: number) => {
  fileList.value.splice(index, 1)
}

// 清空文件列表
const clearAll = () => {
  fileList.value = []
  uploadRef.value?.clearFiles()
}

// 开始上传
const startUpload = () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  uploading.value = true
  uploadRef.value?.submit()
}

// 提交上传（包含文档信息）
const submitUpload = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    if (fileList.value.length === 0) {
      ElMessage.warning('请先选择文件')
      return
    }
    
    uploading.value = true
    
    // 这里应该调用实际的上传API
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    ElMessage.success('文档上传成功')
    
    // 重置表单和文件列表
    formRef.value.resetFields()
    clearAll()
    refreshHistory()
  } catch (error) {
    ElMessage.error('上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

// 获取文件类型
const getFileType = (fileName: string): string => {
  const ext = fileName.split('.').pop()?.toLowerCase()
  const typeMap: Record<string, string> = {
    'pdf': 'PDF',
    'doc': 'Word',
    'docx': 'Word',
    'xls': 'Excel',
    'xlsx': 'Excel',
    'ppt': 'PowerPoint',
    'pptx': 'PowerPoint',
    'jpg': '图片',
    'jpeg': '图片',
    'png': '图片',
    'gif': '图片',
    'txt': '文本'
  }
  return typeMap[ext || ''] || '未知'
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 格式化日期
const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// 获取状态类型
const getStatusType = (status: string): string => {
  const typeMap: Record<string, string> = {
    '上传成功': 'success',
    '处理中': 'warning',
    '上传失败': 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取总文件大小
const getTotalSize = (): string => {
  const total = fileList.value.reduce((sum, file) => sum + file.size, 0)
  return formatFileSize(total)
}

// 查看文档
const viewDocument = (id: string) => {
  router.push(`/knowledge/documents/detail/${id}`)
}

// 下载文档
const downloadDocument = (id: string) => {
  ElMessage.success('开始下载文档')
}

// 刷新上传历史
const refreshHistory = async () => {
  try {
    historyLoading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    uploadHistory.value = [
      {
        id: '1',
        name: '产品需求文档.docx',
        size: 2048576,
        uploadTime: '2024-01-20T10:30:00Z',
        status: '上传成功'
      },
      {
        id: '2',
        name: '系统架构图.pdf',
        size: 5242880,
        uploadTime: '2024-01-19T14:20:00Z',
        status: '处理中'
      },
      {
        id: '3',
        name: '用户手册.pdf',
        size: 3145728,
        uploadTime: '2024-01-18T09:15:00Z',
        status: '上传成功'
      }
    ]
  } catch (error) {
    ElMessage.error('获取上传历史失败')
  } finally {
    historyLoading.value = false
  }
}

onMounted(() => {
  refreshHistory()
})
</script>

<style scoped>
.document-upload {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.upload-header {
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

.upload-section {
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

.upload-tips {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 14px;
}

.upload-area {
  margin: 20px 0;
}

.upload-dragger {
  width: 100%;
}

.upload-content {
  padding: 40px 20px;
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text .primary-text {
  font-size: 16px;
  color: #606266;
  margin: 0 0 8px 0;
}

.upload-text .primary-text em {
  color: #409eff;
  font-style: normal;
}

.upload-text .secondary-text {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.file-list-section {
  margin-bottom: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-header h3 {
  margin: 0;
}

.list-actions {
  display: flex;
  gap: 12px;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fafafa;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.file-icon {
  color: #409eff;
  font-size: 20px;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.file-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.file-status {
  margin-right: 16px;
  min-width: 120px;
}

.upload-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-progress .el-progress {
  flex: 1;
}

.progress-text {
  font-size: 12px;
  color: #909399;
}

.upload-success,
.upload-error,
.upload-ready {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.upload-success {
  color: #67c23a;
}

.upload-error {
  color: #f56c6c;
}

.upload-ready {
  color: #909399;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.document-form-section {
  margin-bottom: 20px;
}

.upload-history-section {
  margin-bottom: 20px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-header h3 {
  margin: 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: #f5f7fa;
}

.history-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.history-icon {
  color: #409eff;
  font-size: 20px;
}

.history-details {
  flex: 1;
}

.history-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.history-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.history-status {
  margin-right: 16px;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.empty-history {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.bottom-actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: #fff;
  border-top: 1px solid #ebeef5;
  padding: 16px 20px;
  z-index: 1000;
}

.actions-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.upload-summary {
  color: #606266;
  font-size: 14px;
}

.actions-buttons {
  display: flex;
  gap: 12px;
}

@media (max-width: 768px) {
  .document-upload {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .card-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .file-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .file-status {
    margin-right: 0;
    width: 100%;
  }
  
  .history-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .actions-content {
    flex-direction: column;
    gap: 12px;
  }
}
</style>