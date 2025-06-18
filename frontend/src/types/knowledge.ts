// 实体类型枚举
export enum EntityType {
  PERSON = 'person',
  ORGANIZATION = 'organization',
  LOCATION = 'location',
  EVENT = 'event',
  CONCEPT = 'concept',
  DOCUMENT = 'document',
  PRODUCT = 'product',
  TECHNOLOGY = 'technology',
  OTHER = 'other'
}

// 关系类型枚举
export enum RelationType {
  RELATED_TO = 'related_to',
  PART_OF = 'part_of',
  BELONGS_TO = 'belongs_to',
  LOCATED_IN = 'located_in',
  WORKS_FOR = 'works_for',
  CREATED_BY = 'created_by',
  DEPENDS_ON = 'depends_on',
  SIMILAR_TO = 'similar_to',
  OPPOSITE_TO = 'opposite_to',
  CAUSES = 'causes',
  ENABLES = 'enables',
  IMPLEMENTS = 'implements',
  EXTENDS = 'extends',
  USES = 'uses',
  CONTAINS = 'contains',
  REFERENCES = 'references'
}

// 文档状态枚举
export enum DocumentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  PROCESSED = 'processed',
  FAILED = 'failed',
  ARCHIVED = 'archived'
}

// 文档类型枚举
export enum DocumentType {
  PDF = 'pdf',
  WORD = 'word',
  EXCEL = 'excel',
  POWERPOINT = 'powerpoint',
  TEXT = 'text',
  MARKDOWN = 'markdown',
  HTML = 'html',
  JSON = 'json',
  XML = 'xml',
  CSV = 'csv',
  IMAGE = 'image',
  VIDEO = 'video',
  AUDIO = 'audio',
  OTHER = 'other'
}

// 知识图谱实体
export interface Entity {
  id: string
  name: string
  type: EntityType
  description?: string
  properties: Record<string, any>
  aliases: string[]
  confidence: number
  source: string
  // sourceId?: string // Removed duplicate, assuming it's meant to be optional and primarily from the source document/system ID, not a graph-internal ID.
  metadata: {
    createdAt: string
    updatedAt: string
    createdBy: string
    tags: string[]
    category?: string
    importance: number
    verified: boolean
  }
  position?: {
    x: number
    y: number
  }
  style?: {
    color?: string
    size?: number
    shape?: string
    icon?: string
  }
}

// 知识图谱关系
export interface Relation {
  id: string
  sourceId: string
  targetId: string
  type: RelationType
  label?: string
  description?: string
  properties: Record<string, any>
  confidence: number
  weight: number
  direction: 'directed' | 'undirected'
  source: string
  // sourceId?: string // Removed duplicate, assuming it's meant to be optional and primarily from the source document/system ID, not a graph-internal ID.
  metadata: {
    createdAt: string
    updatedAt: string
    createdBy: string
    tags: string[]
    verified: boolean
  }
  style?: {
    color?: string
    width?: number
    style?: 'solid' | 'dashed' | 'dotted'
    arrow?: boolean
  }
}

// 文档信息
export interface Document {
  id: string
  title: string
  filename: string
  type: DocumentType
  size: number
  status: DocumentStatus
  content?: string
  summary?: string
  keywords: string[]
  entities: string[] // 实体ID列表
  relations: string[] // 关系ID列表
  metadata: {
    author?: string
    createdAt: string
    updatedAt: string
    uploadedBy: string
    processedAt?: string
    language?: string
    encoding?: string
    pages?: number
    words?: number
    characters?: number
  }
  processing: {
    progress: number
    stage: string
    error?: string
    logs: ProcessingLog[]
  }
  embeddings?: {
    model: string
    vector: number[]
    dimension: number
  }
  chunks?: DocumentChunk[]
}

// 文档处理日志
export interface ProcessingLog {
  timestamp: string
  level: 'info' | 'warning' | 'error'
  message: string
  details?: any
}

// 文档分块
export interface DocumentChunk {
  id: string
  documentId: string
  content: string
  startIndex: number
  endIndex: number
  metadata: {
    page?: number
    section?: string
    heading?: string
    type: 'paragraph' | 'heading' | 'list' | 'table' | 'image' | 'other'
  }
  embeddings?: {
    model: string
    vector: number[]
    dimension: number
  }
  entities: string[]
  relations: string[]
}

// 知识图谱
export interface KnowledgeGraph {
  id: string
  name: string
  description?: string
  status?: string // Added status property
  entities: Entity[]
  relations: Relation[]
  documents: string[] // 文档ID列表
  metadata: {
    createdAt: string
    updatedAt: string
    createdBy: string
    version: string
    tags: string[]
    isPublic: boolean
  }
  statistics: {
    entityCount: number
    relationCount: number
    documentCount: number
    typeDistribution: Record<EntityType, number>
    relationTypeDistribution: Record<RelationType, number>
  }
  settings: {
    layout: 'force' | 'circular' | 'hierarchical' | 'grid'
    physics: boolean
    clustering: boolean
    filtering: {
      entityTypes: EntityType[]
      relationTypes: RelationType[]
      minConfidence: number
      maxNodes: number
    }
  }
}

// 搜索查询
export interface SearchQuery {
  query: string
  type: 'entity' | 'relation' | 'document' | 'all'
  filters: {
    entityTypes?: EntityType[]
    relationTypes?: RelationType[]
    documentTypes?: DocumentType[]
    dateRange?: [string, string]
    confidence?: [number, number]
    tags?: string[]
    source?: string
  }
  options: {
    fuzzy: boolean
    semantic: boolean
    limit: number
    offset: number
    sortBy: 'relevance' | 'confidence' | 'date' | 'name'
    sortOrder: 'asc' | 'desc'
  }
}

// 搜索结果
export interface SearchResult {
  type: 'entity' | 'relation' | 'document'
  item: Entity | Relation | Document
  score: number
  highlights: string[]
  context?: string
}

// 搜索响应
export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: SearchQuery
  took: number
  suggestions?: string[]
  facets?: {
    entityTypes: Record<EntityType, number>
    relationTypes: Record<RelationType, number>
    documentTypes: Record<DocumentType, number>
    sources: Record<string, number>
    tags: Record<string, number>
  }
}

// 图谱分析结果
export interface GraphAnalysis {
  centrality: {
    betweenness: Record<string, number>
    closeness: Record<string, number>
    degree: Record<string, number>
    pagerank: Record<string, number>
  }
  clustering: {
    communities: string[][]
    modularity: number
    algorithm: string
  }
  paths: {
    shortest: Record<string, Record<string, string[]>>
    allPaths: Record<string, Record<string, string[][]>>
  }
  statistics: {
    density: number
    diameter: number
    averagePathLength: number
    clusteringCoefficient: number
    components: number
  }
}

// 推荐结果
export interface Recommendation {
  type: 'entity' | 'relation' | 'document'
  item: Entity | Relation | Document
  score: number
  reason: string
  context?: {
    sourceEntity?: string
    targetEntity?: string
    path?: string[]
  }
}

// 知识抽取配置
export interface ExtractionConfig {
  entities: {
    enabled: boolean
    types: EntityType[]
    confidence: number
    models: string[]
  }
  relations: {
    enabled: boolean
    types: RelationType[]
    confidence: number
    models: string[]
  }
  preprocessing: {
    language: string
    removeStopwords: boolean
    stemming: boolean
    lemmatization: boolean
    normalization: boolean
  }
  postprocessing: {
    deduplication: boolean
    validation: boolean
    enrichment: boolean
    linking: boolean
  }
}

// 导入/导出格式
export interface ImportExportFormat {
  format: 'json' | 'rdf' | 'csv' | 'graphml' | 'gexf' | 'cypher'
  options: {
    includeMetadata: boolean
    includeDocuments: boolean
    compression: boolean
    encoding: string
  }
}

// 版本信息
export interface Version {
  id: string
  graphId: string
  version: string
  description?: string
  changes: {
    entitiesAdded: number
    entitiesModified: number
    entitiesDeleted: number
    relationsAdded: number
    relationsModified: number
    relationsDeleted: number
  }
  metadata: {
    createdAt: string
    createdBy: string
    size: number
    checksum: string
  }
}

// 协作信息
export interface Collaboration {
  graphId: string
  users: {
    userId: string
    role: 'owner' | 'editor' | 'viewer'
    permissions: string[]
    joinedAt: string
  }[]
  activity: {
    userId: string
    action: string
    target: string
    timestamp: string
    details?: any
  }[]
  comments: {
    id: string
    userId: string
    target: string
    content: string
    createdAt: string
    replies?: any[]
  }[]
}

// API 响应类型
export interface KnowledgeApiResponse<T = any> {
  success: boolean
  message: string
  data: T
  code?: number
  timestamp?: string
}

// 分页查询参数
export interface PaginationQuery {
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// 实体查询参数
export interface EntityQuery extends PaginationQuery {
  keyword?: string
  type?: EntityType
  tags?: string[]
  confidence?: [number, number]
  source?: string
  verified?: boolean
  filter?: any
}

// 关系查询参数
export interface RelationQuery extends PaginationQuery {
  keyword?: string
  type?: RelationType
  sourceId?: string
  targetId?: string
  confidence?: [number, number]
  weight?: [number, number]
  verified?: boolean
  filter?: any
}

// 文档查询参数
export interface DocumentQuery extends PaginationQuery {
  keyword?: string
  type?: DocumentType
  status?: DocumentStatus
  author?: string
  dateRange?: [string, string]
  tags?: string[]
}