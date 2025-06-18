import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { knowledgeApi } from '@/api/knowledge'
import type { 
  Entity, 
  Relation, 
  Document, 
  SearchQuery, 
  SearchResult
} from '@/types/knowledge'

// 知识图谱视图模式
export enum ViewMode {
  GRAPH = 'graph',
  TABLE = 'table',
  CARD = 'card'
}

// 知识图谱统计信息
interface KnowledgeStats {
  totalEntities: number
  totalRelations: number
  totalDocuments: number
  entityTypes: Record<string, number>
  relationTypes: Record<string, number>
  documentTypes: Record<string, number>
}

// 实体过滤器
interface EntityFilter {
  types: string[]
  confidence: [number, number]
  dateRange?: [string, string]
  tags: string[]
  source: string
}

// 关系过滤器
interface RelationFilter {
  types: string[]
  confidence: [number, number]
  dateRange?: [string, string]
  tags: string[]
  source: string
}

// 图谱布局算法
export enum LayoutAlgorithm {
  FORCE = 'force',
  CIRCULAR = 'circular',
  HIERARCHICAL = 'hierarchical',
  GRID = 'grid'
}

export const useKnowledgeStore = defineStore('knowledge', () => {
  // 实体相关状态
  const entities = ref<Entity[]>([])
  const selectedEntities = ref<Entity[]>([])
  const entityFilter = ref<EntityFilter>({
      types: [],
      confidence: [0, 1],
      source: '',
      tags: []
    })
  const entitiesLoading = ref(false)
  const entitiesTotal = ref(0)
  const entitiesPage = ref(1)
  const entitiesPageSize = ref(20)
  
  // 关系相关状态
  const relations = ref<Relation[]>([])
  const selectedRelations = ref<Relation[]>([])
  const relationFilter = ref<RelationFilter>({
      types: [],
      confidence: [0, 1],
      source: '',
      tags: []
    })
  const relationsLoading = ref(false)
  const relationsTotal = ref(0)
  const relationsPage = ref(1)
  const relationsPageSize = ref(20)
  
  // 文档相关状态
  const documents = ref<Document[]>([])
  const selectedDocuments = ref<Document[]>([])
  const documentsLoading = ref(false)
  const documentsTotal = ref(0)
  const documentsPage = ref(1)
  const documentsPageSize = ref(20)
  
  // 搜索相关状态
  const searchQuery = ref<SearchQuery>({
    query: '',
    type: 'all',
    filters: {},
    options: {
      fuzzy: false,
      semantic: false,
      limit: 10,
      offset: 0,
      sortBy: 'relevance',
      sortOrder: 'desc'
    }
  })
  const searchResults = ref<SearchResult[]>([])
  const searchLoading = ref(false)
  const searchTotal = ref(0)
  const searchHistory = ref<string[]>([])
  
  // 图谱可视化状态
  const viewMode = ref<ViewMode>(ViewMode.GRAPH)
  const layoutAlgorithm = ref<LayoutAlgorithm>(LayoutAlgorithm.FORCE)
  const graphData = ref<{ nodes: any[], edges: any[] }>({ nodes: [], edges: [] })
  const graphLoading = ref(false)
  const selectedNodes = ref<string[]>([])
  const selectedEdges = ref<string[]>([])
  const graphConfig = ref({
    showLabels: true,
    showArrows: true,
    nodeSize: 'degree',
    edgeWidth: 'weight',
    colorScheme: 'category',
    physics: true,
    clustering: false
  })
  
  // 统计信息
  const stats = ref<KnowledgeStats>({
    totalEntities: 0,
    totalRelations: 0,
    totalDocuments: 0,
    entityTypes: {},
    relationTypes: {},
    documentTypes: {}
  })
  const statsLoading = ref(false)
  
  // 计算属性
  const filteredEntities = computed(() => {
    return entities.value.filter(entity => {
      const filter = entityFilter.value
      
      // 类型过滤
      if (filter.types.length > 0 && !filter.types.includes(entity.type)) {
        return false
      }
      
      // 置信度过滤
      if (entity.confidence < filter.confidence[0] || 
          entity.confidence > filter.confidence[1]) {
        return false
      }
      
      // 来源过滤
      if (filter.source && entity.source !== filter.source) {
        return false
      }
      
      // 日期范围过滤
      if (filter.dateRange.length === 2) {
        const entityDate = new Date(entity.metadata.createdAt)
        const startDate = new Date(filter.dateRange[0])
        const endDate = new Date(filter.dateRange[1])
        
        if (entityDate < startDate || entityDate > endDate) {
          return false
        }
      }
      
      return true
    })
  })
  
  const filteredRelations = computed(() => {
    return relations.value.filter(relation => {
      const filter = relationFilter.value
      
      // 类型过滤
      if (filter.types.length > 0 && !filter.types.includes(relation.type)) {
        return false
      }
      
      // 置信度过滤
      if (relation.confidence < filter.confidence[0] || 
          relation.confidence > filter.confidence[1]) {
        return false
      }
      
      // 来源过滤
      if (filter.source && relation.source !== filter.source) {
        return false
      }
      
      // 日期范围过滤
      if (filter.dateRange.length === 2) {
        const relationDate = new Date(relation.metadata.createdAt)
        const startDate = new Date(filter.dateRange[0])
        const endDate = new Date(filter.dateRange[1])
        
        if (relationDate < startDate || relationDate > endDate) {
          return false
        }
      }
      
      return true
    })
  })
  
  const entityTypes = computed(() => {
    const types = new Set(entities.value.map(entity => entity.type))
    return Array.from(types)
  })
  
  const relationTypes = computed(() => {
    const types = new Set(relations.value.map(relation => relation.type))
    return Array.from(types)
  })
  
  const hasSelection = computed(() => {
    return selectedEntities.value.length > 0 || 
           selectedRelations.value.length > 0 || 
           selectedDocuments.value.length > 0
  })
  
  // 实体相关动作
  const fetchEntities = async (page = 1, pageSize = 20) => {
    try {
      entitiesLoading.value = true
      entitiesPage.value = page
      entitiesPageSize.value = pageSize
      
      const response = await knowledgeApi.getEntities({
        page,
        pageSize,
        filter: entityFilter.value
      })
      
      entities.value = response.data.items
      entitiesTotal.value = response.data.total
    } catch (error: any) {
      console.error('获取实体列表失败:', error)
      ElMessage.error(error.message || '获取实体列表失败')
    } finally {
      entitiesLoading.value = false
    }
  }
  
  const createEntity = async (entityData: Omit<Entity, 'id' | 'createdAt' | 'updatedAt'>) => {
    try {
      const response = await knowledgeApi.createEntity(entityData)
      
      entities.value.unshift(response.data)
      entitiesTotal.value += 1
      
      ElMessage.success('实体创建成功')
      return response.data
    } catch (error: any) {
      console.error('实体创建失败:', error)
      ElMessage.error(error.message || '实体创建失败')
      return null
    }
  }
  
  const updateEntity = async (entityId: string, entityData: Partial<Entity>) => {
    try {
      const response = await knowledgeApi.updateEntity(entityId, entityData)
      
      const index = entities.value.findIndex(entity => entity.id === entityId)
      if (index !== -1) {
        entities.value[index] = { ...entities.value[index], ...response.data }
      }
      
      ElMessage.success('实体更新成功')
        return response.data
    } catch (error: any) {
      console.error('实体更新失败:', error)
      ElMessage.error(error.message || '实体更新失败')
      return null
    }
  }
  
  const deleteEntity = async (entityId: string) => {
    try {
      const response = await knowledgeApi.deleteEntity(entityId)
      
      entities.value = entities.value.filter(entity => entity.id !== entityId)
      entitiesTotal.value -= 1
      
      // 移除选中状态
      selectedEntities.value = selectedEntities.value.filter(
        entity => entity.id !== entityId
      )
      
      ElMessage.success('实体删除成功')
      return true
    } catch (error: any) {
      console.error('实体删除失败:', error)
      ElMessage.error(error.message || '实体删除失败')
      return false
    }
  }
  
  const batchDeleteEntities = async (entityIds: string[]) => {
    try {
      const response = await knowledgeApi.batchDeleteEntities(entityIds)
      
      entities.value = entities.value.filter(
        entity => !entityIds.includes(entity.id)
      )
      entitiesTotal.value -= entityIds.length
      
      // 清除选中状态
      selectedEntities.value = []
      
      ElMessage.success(`成功删除 ${entityIds.length} 个实体`)
      return true
    } catch (error: any) {
      console.error('批量删除实体失败:', error)
      ElMessage.error(error.message || '批量删除实体失败')
      return false
    }
  }
  
  // 关系相关动作
  const fetchRelations = async (page = 1, pageSize = 20) => {
    try {
      relationsLoading.value = true
      relationsPage.value = page
      relationsPageSize.value = pageSize
      
      const response = await knowledgeApi.getRelations({
        page,
        pageSize,
        filter: relationFilter.value
      })
      
      relations.value = response.data.items
      relationsTotal.value = response.data.total
    } catch (error: any) {
      console.error('获取关系列表失败:', error)
      ElMessage.error(error.message || '获取关系列表失败')
    } finally {
      relationsLoading.value = false
    }
  }
  
  const createRelation = async (relationData: Omit<Relation, 'id' | 'createdAt' | 'updatedAt'>) => {
    try {
      const response = await knowledgeApi.createRelation(relationData)
      
      relations.value.unshift(response.data)
      relationsTotal.value += 1
      
      ElMessage.success('关系创建成功')
      return response.data
    } catch (error: any) {
      console.error('关系创建失败:', error)
      ElMessage.error(error.message || '关系创建失败')
      return null
    }
  }
  
  const deleteRelation = async (relationId: string) => {
    try {
      const response = await knowledgeApi.deleteRelation(relationId)
      
      relations.value = relations.value.filter(relation => relation.id !== relationId)
      relationsTotal.value -= 1
      
      ElMessage.success('关系删除成功')
      return true
    } catch (error: any) {
      console.error('关系删除失败:', error)
      ElMessage.error(error.message || '关系删除失败')
      return false
    }
  }
  
  // 文档相关动作
  const fetchDocuments = async (page = 1, pageSize = 20) => {
    try {
      documentsLoading.value = true
      documentsPage.value = page
      documentsPageSize.value = pageSize
      
      const response = await knowledgeApi.getDocuments({
        page,
        pageSize
      })
      
      documents.value = response.data.items
      documentsTotal.value = response.data.total
    } catch (error: any) {
      console.error('获取文档列表失败:', error)
      ElMessage.error(error.message || '获取文档列表失败')
    } finally {
      documentsLoading.value = false
    }
  }
  
  const uploadDocument = async (file: File, metadata?: any) => {
    try {
      const response = await knowledgeApi.uploadDocument(file, metadata)
      
      documents.value.unshift(response.data)
      documentsTotal.value += 1
      
      ElNotification({
        title: '文档上传成功',
        message: `文档 "${file.name}" 已成功上传`,
        type: 'success',
        duration: 3000
      })
      
      return response.data
    } catch (error: any) {
      console.error('文档上传失败:', error)
      ElMessage.error(error.message || '文档上传失败')
      return null
    }
  }
  
  const deleteDocument = async (documentId: string) => {
    try {
      const response = await knowledgeApi.deleteDocument(documentId)
      
      documents.value = documents.value.filter(doc => doc.id !== documentId)
      documentsTotal.value -= 1
      
      ElMessage.success('文档删除成功')
      return true
    } catch (error: any) {
      console.error('文档删除失败:', error)
      ElMessage.error(error.message || '文档删除失败')
      return false
    }
  }
  
  // 搜索相关动作
  const search = async (query: SearchQuery) => {
    try {
      searchLoading.value = true
      searchQuery.value = { ...query }
      
      const response = await knowledgeApi.searchKnowledge(query)
      
      searchResults.value = response.data.results || []
      searchTotal.value = response.data.total || 0
      
      return response.data
    } catch (error: any) {
      console.error('搜索失败:', error)
      ElMessage.error(error.message || '搜索失败')
      return null
    } finally {
      searchLoading.value = false
    }
  }
  
  const clearSearchResults = () => {
    searchResults.value = []
    searchQuery.value = {
      query: '',
      type: 'all',
      filters: {},
      options: {
        fuzzy: false,
        semantic: false,
        limit: 10,
        offset: 0,
        sortBy: 'relevance',
        sortOrder: 'desc'
      }
    }
  }
  
  const clearSearchHistory = () => {
    searchHistory.value = []
    saveSearchHistory()
  }
  
  // 图谱可视化动作
  const fetchGraphData = async (options?: any) => {
    try {
      graphLoading.value = true
      
      const response = await knowledgeApi.getGraphData(options)
      
      graphData.value = response.data
      return response.data
    } catch (error: any) {
      console.error('获取图谱数据失败:', error)
      ElMessage.error(error.message || '获取图谱数据失败')
      return null
    } finally {
      graphLoading.value = false
    }
  }
  
  const setViewMode = (mode: ViewMode) => {
    viewMode.value = mode
    saveSettings()
  }
  
  const setLayoutAlgorithm = (algorithm: LayoutAlgorithm) => {
    layoutAlgorithm.value = algorithm
    saveSettings()
  }
  
  const updateGraphConfig = (config: Partial<typeof graphConfig.value>) => {
    Object.assign(graphConfig.value, config)
    saveSettings()
  }
  
  // 统计信息动作
  const fetchStats = async () => {
    try {
      statsLoading.value = true
      
      const response = await knowledgeApi.getStats()
      
      stats.value = response.data
      return response.data
    } catch (error: any) {
      console.error('获取统计信息失败:', error)
      ElMessage.error(error.message || '获取统计信息失败')
      return null
    } finally {
      statsLoading.value = false
    }
  }
  
  // 选择相关动作
  const selectEntity = (entity: Entity) => {
    const index = selectedEntities.value.findIndex(e => e.id === entity.id)
    if (index === -1) {
      selectedEntities.value.push(entity)
    }
  }
  
  const unselectEntity = (entityId: string) => {
    selectedEntities.value = selectedEntities.value.filter(e => e.id !== entityId)
  }
  
  const toggleEntitySelection = (entity: Entity) => {
    const index = selectedEntities.value.findIndex(e => e.id === entity.id)
    if (index === -1) {
      selectedEntities.value.push(entity)
    } else {
      selectedEntities.value.splice(index, 1)
    }
  }
  
  const clearEntitySelection = () => {
    selectedEntities.value = []
  }
  
  const selectAllEntities = () => {
    selectedEntities.value = [...filteredEntities.value]
  }
  
  // 过滤器动作
  const updateEntityFilter = (filter: Partial<EntityFilter>) => {
    Object.assign(entityFilter.value, filter)
    fetchEntities(1, entitiesPageSize.value)
  }
  
  const updateRelationFilter = (filter: Partial<RelationFilter>) => {
    Object.assign(relationFilter.value, filter)
    fetchRelations(1, relationsPageSize.value)
  }
  
  const resetFilters = () => {
    entityFilter.value = {
        types: [],
        confidence: [0, 1],
        source: '',
        tags: []
      }
    
    relationFilter.value = {
        types: [],
        confidence: [0, 1],
        source: '',
        tags: []
      }
    
    fetchEntities(1, entitiesPageSize.value)
    fetchRelations(1, relationsPageSize.value)
  }
  
  // 本地存储相关
  const saveSettings = () => {
    try {
      const settings = {
        viewMode: viewMode.value,
        layoutAlgorithm: layoutAlgorithm.value,
        graphConfig: graphConfig.value
      }
      
      localStorage.setItem('knowledge-settings', JSON.stringify(settings))
    } catch (error) {
      console.error('保存知识图谱设置失败:', error)
    }
  }
  
  const loadSettings = () => {
    try {
      const settings = localStorage.getItem('knowledge-settings')
      if (settings) {
        const parsed = JSON.parse(settings)
        
        viewMode.value = parsed.viewMode || ViewMode.GRAPH
        layoutAlgorithm.value = parsed.layoutAlgorithm || LayoutAlgorithm.FORCE
        Object.assign(graphConfig.value, parsed.graphConfig || {})
      }
    } catch (error) {
      console.error('加载知识图谱设置失败:', error)
    }
  }
  
  const saveSearchHistory = () => {
    try {
      localStorage.setItem('search-history', JSON.stringify(searchHistory.value))
    } catch (error) {
      console.error('保存搜索历史失败:', error)
    }
  }
  
  const loadSearchHistory = () => {
    try {
      const history = localStorage.getItem('search-history')
      if (history) {
        searchHistory.value = JSON.parse(history)
      }
    } catch (error) {
      console.error('加载搜索历史失败:', error)
    }
  }
  
  // 初始化
  loadSettings()
  loadSearchHistory()
  
  return {
    // 实体状态
    entities,
    selectedEntities,
    entityFilter,
    entitiesLoading,
    entitiesTotal,
    entitiesPage,
    entitiesPageSize,
    
    // 关系状态
    relations,
    selectedRelations,
    relationFilter,
    relationsLoading,
    relationsTotal,
    relationsPage,
    relationsPageSize,
    
    // 文档状态
    documents,
    selectedDocuments,
    documentsLoading,
    documentsTotal,
    documentsPage,
    documentsPageSize,
    
    // 搜索状态
    searchQuery,
    searchResults,
    searchLoading,
    searchTotal,
    searchHistory,
    
    // 图谱状态
    viewMode,
    layoutAlgorithm,
    graphData,
    graphLoading,
    selectedNodes,
    selectedEdges,
    graphConfig,
    
    // 统计状态
    stats,
    statsLoading,
    
    // 计算属性
    filteredEntities,
    filteredRelations,
    entityTypes,
    relationTypes,
    hasSelection,
    
    // 实体动作
    fetchEntities,
    createEntity,
    updateEntity,
    deleteEntity,
    batchDeleteEntities,
    
    // 关系动作
    fetchRelations,
    createRelation,
    deleteRelation,
    
    // 文档动作
    fetchDocuments,
    uploadDocument,
    deleteDocument,
    
    // 搜索动作
    search,
    clearSearchResults,
    clearSearchHistory,
    
    // 图谱动作
    fetchGraphData,
    setViewMode,
    setLayoutAlgorithm,
    updateGraphConfig,
    
    // 统计动作
    fetchStats,
    
    // 选择动作
    selectEntity,
    unselectEntity,
    toggleEntitySelection,
    clearEntitySelection,
    selectAllEntities,
    
    // 过滤器动作
    updateEntityFilter,
    updateRelationFilter,
    resetFilters
  }
})