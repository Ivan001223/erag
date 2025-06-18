<template>
  <div class="document-detail">
    <!-- 页面头部 -->
    <div class="detail-header">
      <div class="header-content">
        <div class="breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/knowledge' }">知识库</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ path: '/knowledge/documents' }">文档管理</el-breadcrumb-item>
            <el-breadcrumb-item>{{ document.title || '文档详情' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-actions">
          <el-button type="primary" @click="editDocument">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button @click="downloadDocument">
            <el-icon><Download /></el-icon>
            下载
          </el-button>
          <el-button @click="shareDocument">
            <el-icon><Share /></el-icon>
            分享
          </el-button>
          <el-dropdown @command="handleMoreAction">
            <el-button>
              更多
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="version">版本历史</el-dropdown-item>
                <el-dropdown-item command="export">导出</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 文档信息卡片 -->
    <div class="document-info">
      <el-card>
        <div class="info-content">
          <div class="document-meta">
            <div class="meta-item">
              <span class="label">文档类型：</span>
              <el-tag :type="getTypeColor(document.type)">{{ document.type }}</el-tag>
            </div>
            <div class="meta-item">
              <span class="label">文件大小：</span>
              <span>{{ formatFileSize(document.size) }}</span>
            </div>
            <div class="meta-item">
              <span class="label">创建时间：</span>
              <span>{{ formatDate(document.createdAt) }}</span>
            </div>
            <div class="meta-item">
              <span class="label">更新时间：</span>
              <span>{{ formatDate(document.updatedAt) }}</span>
            </div>
            <div class="meta-item">
              <span class="label">创建者：</span>
              <span>{{ document.creator }}</span>
            </div>
            <div class="meta-item">
              <span class="label">状态：</span>
              <el-tag :type="getStatusColor(document.status)">{{ document.status }}</el-tag>
            </div>
          </div>
          
          <div class="document-stats">
            <div class="stat-item">
              <div class="stat-value">{{ document.viewCount || 0 }}</div>
              <div class="stat-label">浏览次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ document.downloadCount || 0 }}</div>
              <div class="stat-label">下载次数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ document.shareCount || 0 }}</div>
              <div class="stat-label">分享次数</div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 文档内容 -->
    <div class="document-content">
      <el-card>
        <template #header>
          <div class="content-header">
            <h2>{{ document.title }}</h2>
            <div class="content-actions">
              <el-button size="small" @click="toggleFullscreen">
                <el-icon><FullScreen /></el-icon>
                全屏预览
              </el-button>
            </div>
          </div>
        </template>
        
        <div class="content-body" v-loading="contentLoading">
          <!-- 文本内容 -->
          <div v-if="document.type === 'text'" class="text-content" v-html="document.content"></div>
          
          <!-- PDF 预览 -->
          <div v-else-if="document.type === 'pdf'" class="pdf-preview">
            <iframe :src="document.previewUrl" width="100%" height="600px"></iframe>
          </div>
          
          <!-- 图片预览 -->
          <div v-else-if="document.type === 'image'" class="image-preview">
            <el-image :src="document.url" fit="contain" style="width: 100%; max-height: 600px;" />
          </div>
          
          <!-- 其他文件类型 -->
          <div v-else class="file-preview">
            <div class="preview-placeholder">
              <el-icon size="64"><Document /></el-icon>
              <p>此文件类型暂不支持在线预览</p>
              <el-button type="primary" @click="downloadDocument">下载查看</el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 相关信息 -->
    <div class="document-related">
      <el-row :gutter="20">
        <!-- 标签和分类 -->
        <el-col :span="12">
          <el-card>
            <template #header>
              <h3>标签和分类</h3>
            </template>
            <div class="tags-section">
              <div class="tag-group">
                <span class="group-label">分类：</span>
                <el-tag v-for="category in document.categories" :key="category" class="tag-item">
                  {{ category }}
                </el-tag>
              </div>
              <div class="tag-group">
                <span class="group-label">标签：</span>
                <el-tag v-for="tag in document.tags" :key="tag" type="info" class="tag-item">
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- 相关文档 -->
        <el-col :span="12">
          <el-card>
            <template #header>
              <h3>相关文档</h3>
            </template>
            <div class="related-docs">
              <div v-for="doc in relatedDocuments" :key="doc.id" class="related-item" @click="viewDocument(doc.id)">
                <div class="doc-icon">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="doc-info">
                  <div class="doc-title">{{ doc.title }}</div>
                  <div class="doc-meta">{{ formatDate(doc.updatedAt) }}</div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 评论和讨论 -->
    <div class="document-comments">
      <el-card>
        <template #header>
          <div class="comments-header">
            <h3>评论和讨论</h3>
            <el-button type="primary" size="small" @click="showCommentDialog = true">
              添加评论
            </el-button>
          </div>
        </template>
        
        <div class="comments-list">
          <div v-for="comment in comments" :key="comment.id" class="comment-item">
            <div class="comment-avatar">
              <el-avatar :src="comment.avatar" :alt="comment.author">{{ comment.author.charAt(0) }}</el-avatar>
            </div>
            <div class="comment-content">
              <div class="comment-header">
                <span class="author">{{ comment.author }}</span>
                <span class="time">{{ formatDate(comment.createdAt) }}</span>
              </div>
              <div class="comment-text">{{ comment.content }}</div>
              <div class="comment-actions">
                <el-button text size="small" @click="replyComment(comment.id)">回复</el-button>
                <el-button text size="small" @click="likeComment(comment.id)">
                  <el-icon><Like /></el-icon>
                  {{ comment.likes || 0 }}
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 评论对话框 -->
    <el-dialog v-model="showCommentDialog" title="添加评论" width="500px">
      <el-form :model="commentForm" label-width="80px">
        <el-form-item label="评论内容">
          <el-input
            v-model="commentForm.content"
            type="textarea"
            :rows="4"
            placeholder="请输入您的评论..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCommentDialog = false">取消</el-button>
        <el-button type="primary" @click="submitComment">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Edit,
  Download,
  Share,
  ArrowDown,
  FullScreen,
  Document,
  Star as Like
} from '@element-plus/icons-vue'

interface DocumentInfo {
  id: string
  title: string
  type: string
  size: number
  content?: string
  url?: string
  previewUrl?: string
  createdAt: string
  updatedAt: string
  creator: string
  status: string
  viewCount: number
  downloadCount: number
  shareCount: number
  categories: string[]
  tags: string[]
}

interface Comment {
  id: string
  author: string
  avatar?: string
  content: string
  createdAt: string
  likes: number
}

const route = useRoute()
const router = useRouter()

const contentLoading = ref(false)
const showCommentDialog = ref(false)

const document = ref<DocumentInfo>({
  id: '',
  title: '',
  type: 'text',
  size: 0,
  createdAt: '',
  updatedAt: '',
  creator: '',
  status: 'published',
  viewCount: 0,
  downloadCount: 0,
  shareCount: 0,
  categories: [],
  tags: []
})

const relatedDocuments = ref<DocumentInfo[]>([])
const comments = ref<Comment[]>([])

const commentForm = reactive({
  content: ''
})

// 获取文档详情
const fetchDocumentDetail = async () => {
  try {
    contentLoading.value = true
    const documentId = route.params.id as string
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    document.value = {
      id: documentId,
      title: '企业知识管理系统设计文档',
      type: 'text',
      size: 2048576,
      content: '<h1>企业知识管理系统</h1><p>这是一个完整的企业知识管理系统设计文档...</p>',
      createdAt: '2024-01-15T10:30:00Z',
      updatedAt: '2024-01-20T14:20:00Z',
      creator: '张三',
      status: 'published',
      viewCount: 156,
      downloadCount: 23,
      shareCount: 8,
      categories: ['技术文档', '系统设计'],
      tags: ['知识管理', 'Vue.js', 'FastAPI', '企业应用']
    }
    
    // 获取相关文档
    relatedDocuments.value = [
      {
        id: '2',
        title: 'API接口设计规范',
        updatedAt: '2024-01-18T09:15:00Z'
      },
      {
        id: '3',
        title: '数据库设计文档',
        updatedAt: '2024-01-16T16:45:00Z'
      }
    ] as DocumentInfo[]
    
    // 获取评论
    comments.value = [
      {
        id: '1',
        author: '李四',
        content: '这个设计文档很详细，对我们的项目很有帮助！',
        createdAt: '2024-01-21T10:30:00Z',
        likes: 5
      },
      {
        id: '2',
        author: '王五',
        content: '建议在架构图部分增加更多的说明。',
        createdAt: '2024-01-20T15:20:00Z',
        likes: 2
      }
    ]
  } catch (error) {
    ElMessage.error('获取文档详情失败')
  } finally {
    contentLoading.value = false
  }
}

// 编辑文档
const editDocument = () => {
  router.push(`/knowledge/documents/edit/${document.value.id}`)
}

// 下载文档
const downloadDocument = () => {
  ElMessage.success('开始下载文档')
}

// 分享文档
const shareDocument = () => {
  ElMessage.success('分享链接已复制到剪贴板')
}

// 更多操作
const handleMoreAction = (command: string) => {
  switch (command) {
    case 'version':
      ElMessage.info('查看版本历史')
      break
    case 'export':
      ElMessage.info('导出文档')
      break
    case 'delete':
      ElMessageBox.confirm('确定要删除这个文档吗？', '确认删除', {
        type: 'warning'
      }).then(() => {
        ElMessage.success('文档已删除')
        router.push('/knowledge/documents')
      })
      break
  }
}

// 全屏预览
const toggleFullscreen = () => {
  ElMessage.info('全屏预览功能')
}

// 查看文档
const viewDocument = (id: string) => {
  router.push(`/knowledge/documents/detail/${id}`)
}

// 回复评论
const replyComment = (commentId: string) => {
  ElMessage.info(`回复评论 ${commentId}`)
}

// 点赞评论
const likeComment = (commentId: string) => {
  const comment = comments.value.find(c => c.id === commentId)
  if (comment) {
    comment.likes++
    ElMessage.success('点赞成功')
  }
}

// 提交评论
const submitComment = () => {
  if (!commentForm.content.trim()) {
    ElMessage.warning('请输入评论内容')
    return
  }
  
  const newComment: Comment = {
    id: Date.now().toString(),
    author: '当前用户',
    content: commentForm.content,
    createdAt: new Date().toISOString(),
    likes: 0
  }
  
  comments.value.unshift(newComment)
  commentForm.content = ''
  showCommentDialog.value = false
  ElMessage.success('评论添加成功')
}

// 工具函数
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const getTypeColor = (type: string): string => {
  const colors: Record<string, string> = {
    'text': 'primary',
    'pdf': 'success',
    'image': 'warning',
    'video': 'info'
  }
  return colors[type] || 'default'
}

const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    'published': 'success',
    'draft': 'warning',
    'archived': 'info'
  }
  return colors[status] || 'default'
}

onMounted(() => {
  fetchDocumentDetail()
})
</script>

<style scoped>
.document-detail {
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

.document-info {
  margin-bottom: 20px;
}

.info-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.document-meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  flex: 1;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-item .label {
  font-weight: 500;
  color: #666;
  min-width: 80px;
}

.document-stats {
  display: flex;
  gap: 24px;
  margin-left: 40px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.document-content {
  margin-bottom: 20px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-header h2 {
  margin: 0;
  font-size: 20px;
}

.content-body {
  min-height: 400px;
}

.text-content {
  line-height: 1.6;
  font-size: 14px;
}

.pdf-preview,
.image-preview {
  text-align: center;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #999;
}

.preview-placeholder p {
  margin: 16px 0;
}

.document-related {
  margin-bottom: 20px;
}

.tags-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tag-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.group-label {
  font-weight: 500;
  color: #666;
  min-width: 50px;
}

.tag-item {
  margin-right: 8px;
}

.related-docs {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.related-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.related-item:hover {
  background-color: #f5f7fa;
}

.doc-icon {
  color: #409eff;
}

.doc-info {
  flex: 1;
}

.doc-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.doc-meta {
  font-size: 12px;
  color: #909399;
}

.document-comments {
  margin-bottom: 20px;
}

.comments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.comments-header h3 {
  margin: 0;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-item {
  display: flex;
  gap: 12px;
}

.comment-avatar {
  flex-shrink: 0;
}

.comment-content {
  flex: 1;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.comment-header .author {
  font-weight: 500;
  color: #303133;
}

.comment-header .time {
  font-size: 12px;
  color: #909399;
}

.comment-text {
  color: #606266;
  line-height: 1.5;
  margin-bottom: 8px;
}

.comment-actions {
  display: flex;
  gap: 16px;
}

@media (max-width: 768px) {
  .document-detail {
    padding: 12px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .info-content {
    flex-direction: column;
    gap: 20px;
  }
  
  .document-meta {
    grid-template-columns: 1fr;
  }
  
  .document-stats {
    margin-left: 0;
    justify-content: space-around;
    width: 100%;
  }
}
</style>