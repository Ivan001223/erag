// 基础响应类型
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data: T
  code?: number
  timestamp?: string
  errors?: ValidationError[]
}

// 分页响应类型
export interface PaginatedResponse<T = any> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
}

// 验证错误
export interface ValidationError {
  field: string
  message: string
  code?: string
  value?: any
}

// 基础查询参数
export interface BaseQuery {
  page?: number
  pageSize?: number
  keyword?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  filters?: Record<string, any>
}

// 文件信息
export interface FileInfo {
  id: string
  name: string
  originalName: string
  size: number
  type: string
  extension: string
  mimeType: string
  url: string
  thumbnailUrl?: string
  hash: string
  metadata: {
    width?: number
    height?: number
    duration?: number
    pages?: number
    encoding?: string
    language?: string
  }
  uploadedBy: string
  uploadedAt: string
  lastModified: string
}

// 上传配置 - 已移至 src/config/index.ts，此处保留别名以兼容
export type { UploadConfig } from '@/config'

// 上传进度
export interface UploadProgress {
  fileId: string
  fileName: string
  loaded: number
  total: number
  percentage: number
  speed: number
  timeRemaining: number
  status: 'pending' | 'uploading' | 'success' | 'error' | 'cancelled'
  error?: string
}

// 菜单项
export interface MenuItem {
  id: string
  title: string
  icon?: string
  path?: string
  component?: string
  redirect?: string
  meta?: {
    title: string
    icon?: string
    hidden?: boolean
    keepAlive?: boolean
    requireAuth?: boolean
    roles?: string[]
    permissions?: string[]
    badge?: string | number
    activeMenu?: string
    noCache?: boolean
    affix?: boolean
  }
  children?: MenuItem[]
  sort: number
  isExternal: boolean
  isFrame: boolean
  status: 'active' | 'inactive'
}

// 面包屑项
export interface BreadcrumbItem {
  title: string
  path?: string
  icon?: string
  disabled?: boolean
}

// 标签页
export interface TabItem {
  name: string
  title: string
  path: string
  icon?: string
  closable: boolean
  cached: boolean
  affix: boolean
  meta?: Record<string, any>
}

// 通知消息
export interface Notification {
  id: string
  title: string
  content: string
  type: 'info' | 'success' | 'warning' | 'error'
  category: string
  priority: 'low' | 'normal' | 'high' | 'urgent'
  read: boolean
  readAt?: string
  createdAt: string
  expiresAt?: string
  actions?: NotificationAction[]
  metadata?: Record<string, any>
}

// 通知操作
export interface NotificationAction {
  label: string
  action: string
  type: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  url?: string
  params?: Record<string, any>
}

// 系统设置
export interface SystemSettings {
  site: {
    name: string
    title: string
    description: string
    keywords: string[]
    logo: string
    favicon: string
    copyright: string
    icp: string
  }
  security: {
    passwordPolicy: {
      minLength: number
      requireUppercase: boolean
      requireLowercase: boolean
      requireNumbers: boolean
      requireSymbols: boolean
      maxAge: number
      historyCount: number
    }
    sessionTimeout: number
    maxLoginAttempts: number
    lockoutDuration: number
    twoFactorAuth: boolean
    ipWhitelist: string[]
  }
  upload: {
    maxFileSize: number
    allowedTypes: string[]
    storageType: 'local' | 'oss' | 's3'
    storageConfig: Record<string, any>
  }
  email: {
    enabled: boolean
    provider: 'smtp' | 'sendgrid' | 'mailgun'
    config: Record<string, any>
    templates: Record<string, string>
  }
  cache: {
    enabled: boolean
    type: 'memory' | 'redis'
    ttl: number
    config: Record<string, any>
  }
  logging: {
    level: 'debug' | 'info' | 'warn' | 'error'
    retention: number
    targets: string[]
  }
}

// 统计数据
export interface Statistics {
  overview: {
    totalUsers: number
    activeUsers: number
    totalDocuments: number
    totalEntities: number
    totalRelations: number
    storageUsed: number
    storageLimit: number
  }
  trends: {
    userGrowth: DataPoint[]
    documentGrowth: DataPoint[]
    entityGrowth: DataPoint[]
    relationGrowth: DataPoint[]
    storageGrowth: DataPoint[]
  }
  distribution: {
    usersByRole: Record<string, number>
    documentsByType: Record<string, number>
    entitiesByType: Record<string, number>
    relationsByType: Record<string, number>
  }
  activity: {
    dailyActiveUsers: DataPoint[]
    dailyUploads: DataPoint[]
    dailySearches: DataPoint[]
    popularDocuments: { id: string; title: string; views: number }[]
    popularEntities: { id: string; name: string; connections: number }[]
  }
}

// 数据点
export interface DataPoint {
  date: string
  value: number
  label?: string
}

// 图表配置
export interface ChartConfig {
  type: 'line' | 'bar' | 'pie' | 'doughnut' | 'radar' | 'scatter'
  data: {
    labels: string[]
    datasets: {
      label: string
      data: number[]
      backgroundColor?: string | string[]
      borderColor?: string | string[]
      borderWidth?: number
      fill?: boolean
    }[]
  }
  options: {
    responsive: boolean
    maintainAspectRatio: boolean
    plugins?: Record<string, any>
    scales?: Record<string, any>
    animation?: Record<string, any>
  }
}

// 表格列配置
export interface TableColumn {
  key: string
  title: string
  dataIndex: string
  width?: number | string
  minWidth?: number
  maxWidth?: number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  filterable?: boolean
  resizable?: boolean
  fixed?: 'left' | 'right'
  ellipsis?: boolean
  render?: (value: any, record: any, index: number) => any
  filters?: { text: string; value: any }[]
  sorter?: boolean | ((a: any, b: any) => number)
}

// 表格配置
export interface TableConfig {
  columns: TableColumn[]
  data: any[]
  loading: boolean
  pagination: {
    current: number
    pageSize: number
    total: number
    showSizeChanger: boolean
    showQuickJumper: boolean
    showTotal: boolean
  }
  selection: {
    enabled: boolean
    type: 'checkbox' | 'radio'
    selectedRowKeys: string[]
    onChange: (selectedRowKeys: string[], selectedRows: any[]) => void
  }
  expandable: {
    enabled: boolean
    expandedRowKeys: string[]
    onExpand: (expanded: boolean, record: any) => void
    expandedRowRender: (record: any) => any
  }
  scroll: {
    x?: number | string
    y?: number | string
  }
}

// 表单字段
export interface FormField {
  name: string
  label: string
  type: 'input' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'date' | 'time' | 'datetime' | 'number' | 'password' | 'email' | 'url' | 'file' | 'image' | 'editor' | 'custom'
  placeholder?: string
  required?: boolean
  disabled?: boolean
  readonly?: boolean
  hidden?: boolean
  defaultValue?: any
  options?: { label: string; value: any; disabled?: boolean }[]
  rules?: ValidationRule[]
  props?: Record<string, any>
  span?: number
  offset?: number
  component?: any
  render?: (field: FormField, value: any, onChange: (value: any) => void) => any
}

// 验证规则
export interface ValidationRule {
  required?: boolean
  message?: string
  type?: 'string' | 'number' | 'boolean' | 'method' | 'regexp' | 'integer' | 'float' | 'array' | 'object' | 'enum' | 'date' | 'url' | 'hex' | 'email'
  pattern?: RegExp
  min?: number
  max?: number
  len?: number
  enum?: any[]
  whitespace?: boolean
  transform?: (value: any) => any
  validator?: (rule: any, value: any, callback: (error?: string) => void) => void
  asyncValidator?: (rule: any, value: any, callback: (error?: string) => void) => Promise<void>
}

// 表单配置
export interface FormConfig {
  fields: FormField[]
  layout: 'horizontal' | 'vertical' | 'inline'
  labelCol?: { span: number; offset?: number }
  wrapperCol?: { span: number; offset?: number }
  size?: 'small' | 'default' | 'large'
  disabled?: boolean
  readonly?: boolean
  colon?: boolean
  validateOnRuleChange?: boolean
  validateTrigger?: string | string[]
  scrollToFirstError?: boolean
}

// 主题配置 - 已移至 src/config/index.ts，此处保留别名以兼容
export type { ThemeConfig } from '@/config'

// 国际化配置 - 已移至 src/config/index.ts，此处保留别名以兼容
export type { I18nConfig } from '@/config'

// 权限配置
export interface PermissionConfig {
  mode: 'role' | 'permission' | 'both'
  defaultRole: string
  guestRole: string
  adminRole: string
  inheritance: boolean
  cache: boolean
  cacheTTL: number
}

// 缓存配置
export interface CacheConfig {
  enabled: boolean
  type: 'memory' | 'localStorage' | 'sessionStorage' | 'indexedDB'
  prefix: string
  ttl: number
  maxSize: number
  compression: boolean
}

// 日志配置 - 已移至 src/config/index.ts，此处保留别名以兼容
export type { LogConfig } from '@/config'

// 错误信息
export interface ErrorInfo {
  code: string | number
  message: string
  details?: any
  stack?: string
  timestamp: string
  url?: string
  userAgent?: string
  userId?: string
}

// 操作结果
export interface OperationResult<T = any> {
  success: boolean
  data?: T
  error?: ErrorInfo
  message?: string
}

// 异步操作状态
export interface AsyncState<T = any> {
  loading: boolean
  data: T | null
  error: ErrorInfo | null
  lastUpdated: string | null
}

// 选项类型
export interface Option<T = any> {
  label: string
  value: T
  disabled?: boolean
  children?: Option<T>[]
  [key: string]: any
}

// 树节点
export interface TreeNode<T = any> {
  key: string
  title: string
  value?: T
  disabled?: boolean
  checkable?: boolean
  selectable?: boolean
  isLeaf?: boolean
  icon?: string
  children?: TreeNode<T>[]
  [key: string]: any
}

// 拖拽数据
export interface DragData {
  type: string
  data: any
  source: string
  target?: string
}

// 快捷键配置
export interface ShortcutConfig {
  key: string
  ctrl?: boolean
  alt?: boolean
  shift?: boolean
  meta?: boolean
  action: string
  description: string
  global?: boolean
  preventDefault?: boolean
}

// 导出类型
// export type { ApiResponse, PaginatedResponse, ValidationError, BaseQuery }