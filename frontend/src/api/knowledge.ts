import Request from '@/utils/request'
import type {
  Entity,
  Relation,
  Document,
  KnowledgeGraph,
  SearchQuery,
  SearchResponse,
  EntityQuery,
  RelationQuery,
  DocumentQuery,
  GraphAnalysis,
  Recommendation,
  ExtractionConfig,
  ImportExportFormat,
  Version,
  Collaboration,
  ApiResponse,
  PaginatedResponse
} from '@/types'

/**
 * 实体相关API
 */

/**
 * 获取实体列表
 * @param params 查询参数
 * @returns 实体列表
 */
export const getEntities = (params: EntityQuery = {}): Promise<ApiResponse<PaginatedResponse<Entity>>> => {
  return Request.get('/knowledge/entities', { params })
}

/**
 * 获取实体详情
 * @param entityId 实体ID
 * @returns 实体详情
 */
export const getEntity = (entityId: string): Promise<ApiResponse<Entity>> => {
  return Request.get(`/knowledge/entities/${entityId}`)
}

/**
 * 创建实体
 * @param data 实体数据
 * @returns 创建的实体
 */
export const createEntity = (data: Omit<Entity, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<Entity>> => {
  return Request.post('/knowledge/entities', data)
}

/**
 * 更新实体
 * @param entityId 实体ID
 * @param data 更新数据
 * @returns 更新的实体
 */
export const updateEntity = (entityId: string, data: Partial<Entity>): Promise<ApiResponse<Entity>> => {
  return Request.put(`/knowledge/entities/${entityId}`, data)
}

/**
 * 删除实体
 * @param entityId 实体ID
 * @returns 删除响应
 */
export const deleteEntity = (entityId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/knowledge/entities/${entityId}`)
}

/**
 * 批量删除实体
 * @param entityIds 实体ID数组
 * @returns 删除响应
 */
export const batchDeleteEntities = (entityIds: string[]): Promise<ApiResponse<{ message: string; deletedCount: number }>> => {
  return Request.post('/knowledge/entities/batch-delete', { entityIds })
}

/**
 * 批量创建实体
 * @param entities 实体数组
 * @returns 创建响应
 */
export const batchCreateEntities = (entities: Omit<Entity, 'id' | 'createdAt' | 'updatedAt'>[]): Promise<ApiResponse<{ message: string; createdCount: number; entities: Entity[] }>> => {
  return Request.post('/knowledge/entities/batch-create', { entities })
}

/**
 * 获取实体关系
 * @param entityId 实体ID
 * @param params 查询参数
 * @returns 关系列表
 */
export const getEntityRelations = (
  entityId: string,
  params: {
    direction?: 'in' | 'out' | 'both'
    relationType?: string
    page?: number
    pageSize?: number
  } = {}
): Promise<ApiResponse<PaginatedResponse<Relation>>> => {
  return Request.get(`/knowledge/entities/${entityId}/relations`, { params })
}

/**
 * 获取实体相关文档
 * @param entityId 实体ID
 * @param params 查询参数
 * @returns 文档列表
 */
export const getEntityDocuments = (
  entityId: string,
  params: {
    page?: number
    pageSize?: number
  } = {}
): Promise<ApiResponse<PaginatedResponse<Document>>> => {
  return Request.get(`/knowledge/entities/${entityId}/documents`, { params })
}

/**
 * 关系相关API
 */

/**
 * 获取关系列表
 * @param params 查询参数
 * @returns 关系列表
 */
export const getRelations = (params: RelationQuery = {}): Promise<ApiResponse<PaginatedResponse<Relation>>> => {
  return Request.get('/knowledge/relations', { params })
}

/**
 * 获取关系详情
 * @param relationId 关系ID
 * @returns 关系详情
 */
export const getRelation = (relationId: string): Promise<ApiResponse<Relation>> => {
  return Request.get(`/knowledge/relations/${relationId}`)
}

/**
 * 创建关系
 * @param data 关系数据
 * @returns 创建的关系
 */
export const createRelation = (data: Omit<Relation, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<Relation>> => {
  return Request.post('/knowledge/relations', data)
}

/**
 * 更新关系
 * @param relationId 关系ID
 * @param data 更新数据
 * @returns 更新的关系
 */
export const updateRelation = (relationId: string, data: Partial<Relation>): Promise<ApiResponse<Relation>> => {
  return Request.put(`/knowledge/relations/${relationId}`, data)
}

/**
 * 删除关系
 * @param relationId 关系ID
 * @returns 删除响应
 */
export const deleteRelation = (relationId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/knowledge/relations/${relationId}`)
}

/**
 * 批量删除关系
 * @param relationIds 关系ID数组
 * @returns 删除响应
 */
export const batchDeleteRelations = (relationIds: string[]): Promise<ApiResponse<{ message: string; deletedCount: number }>> => {
  return Request.post('/knowledge/relations/batch-delete', { relationIds })
}

/**
 * 批量创建关系
 * @param relations 关系数组
 * @returns 创建响应
 */
export const batchCreateRelations = (relations: Omit<Relation, 'id' | 'createdAt' | 'updatedAt'>[]): Promise<ApiResponse<{ message: string; createdCount: number; relations: Relation[] }>> => {
  return Request.post('/knowledge/relations/batch-create', { relations })
}

/**
 * 文档相关API
 */

/**
 * 获取文档列表
 * @param params 查询参数
 * @returns 文档列表
 */
export const getDocuments = (params: DocumentQuery = {}): Promise<ApiResponse<PaginatedResponse<Document>>> => {
  return Request.get('/knowledge/documents', { params })
}

/**
 * 获取文档详情
 * @param documentId 文档ID
 * @returns 文档详情
 */
export const getDocument = (documentId: string): Promise<ApiResponse<Document>> => {
  return Request.get(`/knowledge/documents/${documentId}`)
}

/**
 * 创建文档
 * @param data 文档数据
 * @returns 创建的文档
 */
export const createDocument = (data: Omit<Document, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<Document>> => {
  return Request.post('/knowledge/documents', data)
}

/**
 * 更新文档
 * @param documentId 文档ID
 * @param data 更新数据
 * @returns 更新的文档
 */
export const updateDocument = (documentId: string, data: Partial<Document>): Promise<ApiResponse<Document>> => {
  return Request.put(`/knowledge/documents/${documentId}`, data)
}

/**
 * 删除文档
 * @param documentId 文档ID
 * @returns 删除响应
 */
export const deleteDocument = (documentId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/knowledge/documents/${documentId}`)
}

/**
 * 批量删除文档
 * @param documentIds 文档ID数组
 * @returns 删除响应
 */
export const batchDeleteDocuments = (documentIds: string[]): Promise<ApiResponse<{ message: string; deletedCount: number }>> => {
  return Request.post('/knowledge/documents/batch-delete', { documentIds })
}

/**
 * 上传文档
 * @param file 文档文件
 * @param metadata 文档元数据
 * @returns 上传响应
 */
export const uploadDocument = (
  file: File,
  metadata: {
    title?: string
    description?: string
    tags?: string[]
    category?: string
  } = {}
): Promise<ApiResponse<Document>> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('metadata', JSON.stringify(metadata))
  
  return Request.post('/knowledge/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 批量上传文档
 * @param files 文档文件数组
 * @param metadata 文档元数据
 * @returns 上传响应
 */
export const batchUploadDocuments = (
  files: File[],
  metadata: Record<string, any> = {}
): Promise<ApiResponse<{ message: string; uploadedCount: number; documents: Document[] }>> => {
  const formData = new FormData()
  files.forEach((file, index) => {
    formData.append(`files[${index}]`, file)
  })
  formData.append('metadata', JSON.stringify(metadata))
  
  return Request.post('/knowledge/documents/batch-upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 处理文档（提取知识）
 * @param documentId 文档ID
 * @param config 处理配置
 * @returns 处理响应
 */
export const processDocument = (
  documentId: string,
  config: Partial<ExtractionConfig> = {}
): Promise<ApiResponse<{ message: string; taskId: string }>> => {
  return Request.post(`/knowledge/documents/${documentId}/process`, { config })
}

/**
 * 获取文档处理状态
 * @param taskId 任务ID
 * @returns 处理状态
 */
export const getDocumentProcessStatus = (taskId: string): Promise<ApiResponse<{
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message?: string
  result?: {
    entitiesExtracted: number
    relationsExtracted: number
    chunksCreated: number
  }
}>> => {
  return Request.get(`/knowledge/documents/process-status/${taskId}`)
}

/**
 * 获取文档分块
 * @param documentId 文档ID
 * @param params 查询参数
 * @returns 分块列表
 */
export const getDocumentChunks = (
  documentId: string,
  params: {
    page?: number
    pageSize?: number
  } = {}
): Promise<ApiResponse<PaginatedResponse<any>>> => {
  return Request.get(`/knowledge/documents/${documentId}/chunks`, { params })
}

/**
 * 搜索相关API
 */

/**
 * 搜索知识图谱
 * @param query 搜索查询
 * @returns 搜索结果
 */
export const searchKnowledge = (query: SearchQuery): Promise<ApiResponse<SearchResponse>> => {
  return Request.post('/knowledge/search', query)
}

/**
 * 语义搜索
 * @param query 搜索文本
 * @param params 搜索参数
 * @returns 搜索结果
 */
export const semanticSearch = (
  query: string,
  params: {
    type?: 'entity' | 'relation' | 'document' | 'all'
    limit?: number
    threshold?: number
    filters?: Record<string, any>
  } = {}
): Promise<ApiResponse<SearchResponse>> => {
  return Request.post('/knowledge/semantic-search', { query, ...params })
}

/**
 * 相似性搜索
 * @param entityId 实体ID
 * @param params 搜索参数
 * @returns 相似实体列表
 */
export const findSimilarEntities = (
  entityId: string,
  params: {
    limit?: number
    threshold?: number
    includeRelations?: boolean
  } = {}
): Promise<ApiResponse<Entity[]>> => {
  return Request.get(`/knowledge/entities/${entityId}/similar`, { params })
}

/**
 * 路径搜索
 * @param sourceId 源实体ID
 * @param targetId 目标实体ID
 * @param params 搜索参数
 * @returns 路径列表
 */
export const findPaths = (
  sourceId: string,
  targetId: string,
  params: {
    maxDepth?: number
    maxPaths?: number
    relationTypes?: string[]
  } = {}
): Promise<ApiResponse<Array<{
  path: Array<{ entity: Entity; relation?: Relation }>
  length: number
  score: number
}>>> => {
  return Request.get('/knowledge/paths', {
    params: { sourceId, targetId, ...params }
  })
}

/**
 * 知识图谱相关API
 */

/**
 * 获取知识图谱信息
 * @param graphId 图谱ID
 * @returns 图谱信息
 */
export const getKnowledgeGraph = (graphId: string): Promise<ApiResponse<KnowledgeGraph>> => {
  return Request.get(`/knowledge/graphs/${graphId}`)
}

/**
 * 获取知识图谱列表
 * @param params 查询参数
 * @returns 图谱列表
 */
export const getKnowledgeGraphs = (params: {
  page?: number
  pageSize?: number
  search?: string
  category?: string
} = {}): Promise<ApiResponse<PaginatedResponse<KnowledgeGraph>>> => {
  return Request.get('/knowledge/graphs', { params })
}

/**
 * 创建知识图谱
 * @param data 图谱数据
 * @returns 创建的图谱
 */
export const createKnowledgeGraph = (data: Omit<KnowledgeGraph, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<KnowledgeGraph>> => {
  return Request.post('/knowledge/graphs', data)
}

/**
 * 更新知识图谱
 * @param graphId 图谱ID
 * @param data 更新数据
 * @returns 更新的图谱
 */
export const updateKnowledgeGraph = (graphId: string, data: Partial<KnowledgeGraph>): Promise<ApiResponse<KnowledgeGraph>> => {
  return Request.put(`/knowledge/graphs/${graphId}`, data)
}

/**
 * 删除知识图谱
 * @param graphId 图谱ID
 * @returns 删除响应
 */
export const deleteKnowledgeGraph = (graphId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/knowledge/graphs/${graphId}`)
}

/**
 * 获取图谱统计信息
 * @param graphId 图谱ID
 * @returns 统计信息
 */
export const getGraphStats = (graphId: string): Promise<ApiResponse<{
  entityCount: number
  relationCount: number
  documentCount: number
  entityTypes: Record<string, number>
  relationTypes: Record<string, number>
  documentTypes: Record<string, number>
  lastUpdated: string
}>> => {
  return Request.get(`/knowledge/graphs/${graphId}/stats`)
}

/**
 * 图谱分析
 * @param graphId 图谱ID
 * @param analysisType 分析类型
 * @returns 分析结果
 */
export const analyzeGraph = (
  graphId: string,
  analysisType: 'centrality' | 'community' | 'clustering' | 'pagerank'
): Promise<ApiResponse<GraphAnalysis>> => {
  return Request.post(`/knowledge/graphs/${graphId}/analyze`, { analysisType })
}

/**
 * 获取推荐
 * @param params 推荐参数
 * @returns 推荐结果
 */
export const getRecommendations = (params: {
  type: 'entity' | 'relation' | 'document'
  entityId?: string
  userId?: string
  limit?: number
  context?: Record<string, any>
}): Promise<ApiResponse<Recommendation[]>> => {
  return Request.get('/knowledge/recommendations', { params })
}

/**
 * 导入/导出相关API
 */

/**
 * 导出知识图谱
 * @param graphId 图谱ID
 * @param format 导出格式
 * @param options 导出选项
 * @returns 导出文件
 */
export const exportKnowledgeGraph = (
  graphId: string,
  format: string,
  options: {
    includeDocuments?: boolean
    includeMetadata?: boolean
    filters?: Record<string, any>
  } = {}
): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    Request.download(`/knowledge/graphs/${graphId}/export`, {
      format, ...options
    }, `graph-${graphId}.${format}`)
      .then(() => resolve(new Blob()))
      .catch(reject)
  })
}

/**
 * 导入知识图谱
 * @param file 导入文件
 * @param format 导入格式
 * @param options 导入选项
 * @returns 导入结果
 */
export const importKnowledgeGraph = (
  file: File,
  format: string,
  options: {
    graphId?: string
    mergeStrategy?: 'replace' | 'merge' | 'append'
    validateData?: boolean
  } = {}
): Promise<ApiResponse<{
  message: string
  taskId: string
  graphId: string
}>> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('format', format)
  formData.append('options', JSON.stringify(options))
  
  return Request.post('/knowledge/graphs/import', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 获取导入状态
 * @param taskId 任务ID
 * @returns 导入状态
 */
export const getImportStatus = (taskId: string): Promise<ApiResponse<{
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message?: string
  result?: {
    entitiesImported: number
    relationsImported: number
    documentsImported: number
    errors: string[]
  }
}>> => {
  return Request.get(`/knowledge/import-status/${taskId}`)
}

/**
 * 版本管理相关API
 */

/**
 * 获取图谱版本列表
 * @param graphId 图谱ID
 * @returns 版本列表
 */
export const getGraphVersions = (graphId: string): Promise<ApiResponse<Version[]>> => {
  return Request.get(`/knowledge/graphs/${graphId}/versions`)
}

/**
 * 创建图谱版本
 * @param graphId 图谱ID
 * @param data 版本数据
 * @returns 创建的版本
 */
export const createGraphVersion = (
  graphId: string,
  data: {
    name: string
    description?: string
    tags?: string[]
  }
): Promise<ApiResponse<Version>> => {
  return Request.post(`/knowledge/graphs/${graphId}/versions`, data)
}

/**
 * 恢复到指定版本
 * @param graphId 图谱ID
 * @param versionId 版本ID
 * @returns 恢复响应
 */
export const restoreGraphVersion = (graphId: string, versionId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.post(`/knowledge/graphs/${graphId}/versions/${versionId}/restore`)
}

/**
 * 比较版本
 * @param graphId 图谱ID
 * @param versionId1 版本1 ID
 * @param versionId2 版本2 ID
 * @returns 比较结果
 */
export const compareGraphVersions = (
  graphId: string,
  versionId1: string,
  versionId2: string
): Promise<ApiResponse<{
  entitiesAdded: Entity[]
  entitiesRemoved: Entity[]
  entitiesModified: Array<{ old: Entity; new: Entity }>
  relationsAdded: Relation[]
  relationsRemoved: Relation[]
  relationsModified: Array<{ old: Relation; new: Relation }>
}>> => {
  return Request.get(`/knowledge/graphs/${graphId}/versions/compare`, {
    params: { version1: versionId1, version2: versionId2 }
  })
}

/**
 * 协作相关API
 */

/**
 * 获取协作信息
 * @param graphId 图谱ID
 * @returns 协作信息
 */
export const getCollaborationInfo = (graphId: string): Promise<ApiResponse<Collaboration>> => {
  return Request.get(`/knowledge/graphs/${graphId}/collaboration`)
}

/**
 * 邀请协作者
 * @param graphId 图谱ID
 * @param data 邀请数据
 * @returns 邀请响应
 */
export const inviteCollaborator = (
  graphId: string,
  data: {
    email: string
    role: 'viewer' | 'editor' | 'admin'
    message?: string
  }
): Promise<ApiResponse<{ message: string }>> => {
  return Request.post(`/knowledge/graphs/${graphId}/collaborators/invite`, data)
}

/**
 * 移除协作者
 * @param graphId 图谱ID
 * @param userId 用户ID
 * @returns 移除响应
 */
export const removeCollaborator = (graphId: string, userId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/knowledge/graphs/${graphId}/collaborators/${userId}`)
}

/**
 * 获取关系统计
 * @returns 关系统计信息
 */
export const getRelationStats = (): Promise<ApiResponse<any>> => {
  return Request.get('/knowledge/relations/stats')
}

/**
 * 获取文档统计
 * @returns 文档统计信息
 */
export const getDocumentStats = (): Promise<ApiResponse<any>> => {
  return Request.get('/knowledge/documents/stats')
}

/**
 * 获取实体推荐
 * @param entityId 实体ID
 * @returns 实体推荐列表
 */
export const getEntityRecommendations = (entityId: string): Promise<ApiResponse<any[]>> => {
  return Request.get(`/knowledge/entities/${entityId}/recommendations`)
}

/**
 * 获取关系推荐
 * @param relationId 关系ID
 * @returns 关系推荐列表
 */
export const getRelationRecommendations = (relationId: string): Promise<ApiResponse<any[]>> => {
  return Request.get(`/knowledge/relations/${relationId}/recommendations`)
}

/**
 * 获取抽取配置
 * @returns 抽取配置
 */
export const getExtractionConfig = (): Promise<ApiResponse<any>> => {
  return Request.get('/knowledge/extraction/config')
}

/**
 * 更新抽取配置
 * @param config 配置数据
 * @returns 更新响应
 */
export const updateExtractionConfig = (config: any): Promise<ApiResponse<{ message: string }>> => {
  return Request.put('/knowledge/extraction/config', config)
}

/**
 * 导入数据
 * @param file 导入文件
 * @param options 导入选项
 * @returns 导入结果
 */
export const importData = (file: File, options: any = {}): Promise<ApiResponse<any>> => {
  const formData = new FormData()
  formData.append('file', file)
  Object.keys(options).forEach(key => {
    formData.append(key, options[key])
  })
  return Request.post('/knowledge/import', formData)
}

/**
 * 导出数据
 * @param options 导出选项
 * @returns 导出文件
 */
export const exportData = (options: any = {}): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    Request.download('/knowledge/export', options, 'knowledge-data.json')
      .then(() => resolve(new Blob()))
      .catch(reject)
  })
}

/**
 * 获取导入历史
 * @returns 导入历史列表
 */
export const getImportHistory = (): Promise<ApiResponse<any[]>> => {
  return Request.get('/knowledge/import/history')
}

/**
 * 获取导出历史
 * @returns 导出历史列表
 */
export const getExportHistory = (): Promise<ApiResponse<any[]>> => {
  return Request.get('/knowledge/export/history')
}

/**
 * 获取版本列表
 * @returns 版本列表
 */
export const getVersions = (): Promise<ApiResponse<any[]>> => {
  return Request.get('/knowledge/versions')
}

/**
 * 获取版本详情
 * @param versionId 版本ID
 * @returns 版本详情
 */
export const getVersion = (versionId: string): Promise<ApiResponse<any>> => {
  return Request.get(`/knowledge/versions/${versionId}`)
}

/**
 * 创建版本
 * @param data 版本数据
 * @returns 创建响应
 */
export const createVersion = (data: any): Promise<ApiResponse<any>> => {
  return Request.post('/knowledge/versions', data)
}

/**
 * 恢复版本
 * @param versionId 版本ID
 * @returns 恢复响应
 */
export const restoreVersion = (versionId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.post(`/knowledge/versions/${versionId}/restore`)
}

/**
 * 比较版本
 * @param versionId1 版本1 ID
 * @param versionId2 版本2 ID
 * @returns 比较结果
 */
export const compareVersions = (versionId1: string, versionId2: string): Promise<ApiResponse<any>> => {
  return Request.get('/knowledge/versions/compare', {
    params: { v1: versionId1, v2: versionId2 }
  })
}

/**
 * 更新协作者权限
 * @param graphId 图谱ID
 * @param userId 用户ID
 * @param role 新角色
 * @returns 更新响应
 */
export const updateCollaboratorRole = (
  graphId: string,
  userId: string,
  role: 'viewer' | 'editor' | 'admin'
): Promise<ApiResponse<{ message: string }>> => {
  return Request.put(`/knowledge/graphs/${graphId}/collaborators/${userId}`, { role })
}

/**
 * 通用搜索
 * @param query 搜索查询
 * @returns 搜索结果
 */
export const search = (query: string): Promise<ApiResponse<SearchResponse>> => {
  return Request.get('/knowledge/search', { params: { q: query } })
}

/**
 * 搜索实体
 * @param query 搜索查询
 * @returns 实体搜索结果
 */
export const searchEntities = (query: string): Promise<ApiResponse<PaginatedResponse<Entity>>> => {
  return Request.get('/knowledge/entities/search', { params: { q: query } })
}

/**
 * 搜索关系
 * @param query 搜索查询
 * @returns 关系搜索结果
 */
export const searchRelations = (query: string): Promise<ApiResponse<PaginatedResponse<Relation>>> => {
  return Request.get('/knowledge/relations/search', { params: { q: query } })
}

/**
 * 搜索文档
 * @param query 搜索查询
 * @returns 文档搜索结果
 */
export const searchDocuments = (query: string): Promise<ApiResponse<PaginatedResponse<Document>>> => {
  return Request.get('/knowledge/documents/search', { params: { q: query } })
}

/**
 * 获取搜索建议
 * @param query 搜索查询
 * @returns 搜索建议
 */
export const getSearchSuggestions = (query: string): Promise<ApiResponse<string[]>> => {
  return Request.get('/knowledge/search/suggestions', { params: { q: query } })
}

/**
 * 获取知识图谱列表
 * @param params 查询参数
 * @returns 图谱列表
 */
export const getGraphs = (params: any = {}): Promise<ApiResponse<PaginatedResponse<KnowledgeGraph>>> => {
  return Request.get('/knowledge/graphs', { params })
}

/**
 * 获取知识图谱详情
 * @param graphId 图谱ID
 * @returns 图谱详情
 */
export const getGraph = (graphId: string): Promise<ApiResponse<KnowledgeGraph>> => {
  return Request.get(`/knowledge/graphs/${graphId}`)
}

/**
 * 创建知识图谱
 * @param data 图谱数据
 * @returns 创建的图谱
 */
export const createGraph = (data: Omit<KnowledgeGraph, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<KnowledgeGraph>> => {
  return Request.post('/knowledge/graphs', data)
}

/**
 * 更新知识图谱
 * @param graphId 图谱ID
 * @param data 更新数据
 * @returns 更新的图谱
 */
export const updateGraph = (graphId: string, data: Partial<KnowledgeGraph>): Promise<ApiResponse<KnowledgeGraph>> => {
  return Request.put(`/knowledge/graphs/${graphId}`, data)
}

/**
 * 删除知识图谱
 * @param graphId 图谱ID
 * @returns 删除响应
 */
export const deleteGraph = (graphId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/knowledge/graphs/${graphId}`)
}

/**
 * 获取图谱数据
 * @param graphId 图谱ID
 * @returns 图谱数据
 */
export const getGraphData = (graphId: string): Promise<ApiResponse<any>> => {
  return Request.get(`/knowledge/graphs/${graphId}/data`)
}

/**
 * 获取统计信息
 * @returns 统计信息
 */
export const getStats = (): Promise<ApiResponse<any>> => {
  return Request.get('/knowledge/stats')
}

/**
 * 获取实体统计
 * @returns 实体统计
 */
export const getEntityStats = (): Promise<ApiResponse<any>> => {
  return Request.get('/knowledge/stats/entities')
}

/**
 * 知识图谱API对象
 */
export const knowledgeApi = {
  // 实体相关
  getEntities,
  getEntity,
  createEntity,
  updateEntity,
  deleteEntity,
  batchDeleteEntities,
  batchCreateEntities,
  getEntityRelations,
  
  // 关系相关
  getRelations,
  getRelation,
  createRelation,
  updateRelation,
  deleteRelation,
  batchDeleteRelations,
  batchCreateRelations,
  
  // 文档相关
  getDocuments,
  getDocument,
  uploadDocument,
  updateDocument,
  deleteDocument,
  batchDeleteDocuments,
  processDocument,
  
  // 搜索相关
  search,
  searchKnowledge,
  searchEntities,
  searchRelations,
  searchDocuments,
  getSearchSuggestions,
  
  // 图谱相关
  getGraphs,
  getGraph,
  createGraph,
  updateGraph,
  deleteGraph,
  getGraphData,
  analyzeGraph,
  getGraphStats,
  
  // 统计相关
  getStats,
  getEntityStats,
  getRelationStats,
  getDocumentStats,
  
  // 推荐相关
  getRecommendations,
  getEntityRecommendations,
  getRelationRecommendations,
  
  // 配置相关
  getExtractionConfig,
  updateExtractionConfig,
  
  // 导入导出
  importData,
  exportData,
  getImportHistory,
  getExportHistory,
  
  // 版本相关
  getVersions,
  getVersion,
  createVersion,
  restoreVersion,
  compareVersions,
  
  // 协作相关
  getCollaborationInfo,
  inviteCollaborator,
  removeCollaborator,
  updateCollaboratorRole
}