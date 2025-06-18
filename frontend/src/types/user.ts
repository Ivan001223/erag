// 用户角色枚举
export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  VIEWER = 'viewer'
}

// 用户状态枚举
export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING = 'pending'
}

// 基础用户信息
export interface User {
  id: string
  username: string
  email: string
  nickname?: string
  avatar?: string
  role: UserRole
  status: UserStatus
  permissions: string[]
  lastLoginAt?: string
  createdAt: string
  updatedAt: string
  profile?: UserProfile
}

// 用户详细资料
export interface UserProfile {
  firstName?: string
  lastName?: string
  phone?: string
  department?: string
  position?: string
  bio?: string
  location?: string
  website?: string
  socialLinks?: {
    github?: string
    linkedin?: string
    twitter?: string
  }
  preferences?: UserPreferences
}

// 用户偏好设置
export interface UserPreferences {
  language: 'zh-CN' | 'en-US'
  timezone: string
  dateFormat: string
  timeFormat: '12h' | '24h'
  theme: 'light' | 'dark' | 'auto'
  notifications: NotificationSettings
  privacy: PrivacySettings
}

// 通知设置
export interface NotificationSettings {
  email: {
    enabled: boolean
    frequency: 'immediate' | 'daily' | 'weekly'
    types: string[]
  }
  push: {
    enabled: boolean
    types: string[]
  }
  inApp: {
    enabled: boolean
    types: string[]
  }
}

// 隐私设置
export interface PrivacySettings {
  profileVisibility: 'public' | 'private' | 'contacts'
  showEmail: boolean
  showPhone: boolean
  allowSearch: boolean
  dataSharing: boolean
}

// 登录表单
export interface LoginForm {
  username: string
  password: string
  remember?: boolean
  captcha?: string
}

// 注册表单
export interface RegisterForm {
  username: string
  email: string
  password: string
  confirmPassword: string
  nickname?: string
  agreement: boolean
  captcha?: string
  inviteCode?: string
}

// 忘记密码表单
export interface ForgotPasswordForm {
  email: string
  captcha?: string
}

// 重置密码表单
export interface ResetPasswordForm {
  token: string
  password: string
  confirmPassword: string
}

// 修改密码表单
export interface ChangePasswordForm {
  oldPassword: string
  newPassword: string
  confirmPassword: string
}

// 登录响应
export interface LoginResponse {
  user: User
  token: string
  refreshToken: string
  expiresIn: number
  permissions: string[]
}

// 用户列表查询参数
export interface UserListQuery {
  page?: number
  pageSize?: number
  keyword?: string
  role?: UserRole
  status?: UserStatus
  department?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  dateRange?: [string, string]
}

// 用户列表响应
export interface UserListResponse {
  items: User[]
  total: number
  page: number
  pageSize: number
}

// 用户统计信息
export interface UserStats {
  total: number
  active: number
  inactive: number
  newThisMonth: number
  roleDistribution: Record<UserRole, number>
  departmentDistribution: Record<string, number>
  loginStats: {
    today: number
    thisWeek: number
    thisMonth: number
  }
}

// 用户活动日志
export interface UserActivity {
  id: string
  userId: string
  action: string
  description: string
  ip: string
  userAgent: string
  location?: string
  metadata?: Record<string, any>
  createdAt: string
}

// 用户会话信息
export interface UserSession {
  id: string
  userId: string
  token: string
  ip: string
  userAgent: string
  location?: string
  isActive: boolean
  lastActivity: string
  createdAt: string
  expiresAt: string
}

// 权限定义
export interface Permission {
  id: string
  name: string
  code: string
  description?: string
  category: string
  isSystem: boolean
  createdAt: string
}

// 角色定义
export interface Role {
  id: string
  name: string
  code: string
  description?: string
  permissions: Permission[]
  isSystem: boolean
  userCount: number
  createdAt: string
  updatedAt: string
}

// 部门定义
export interface Department {
  id: string
  name: string
  code: string
  description?: string
  parentId?: string
  level: number
  sort: number
  manager?: User
  userCount: number
  children?: Department[]
  createdAt: string
  updatedAt: string
}

// 邀请码
export interface InviteCode {
  id: string
  code: string
  createdBy: string
  createdByUser?: User
  usedBy?: string
  usedByUser?: User
  maxUses: number
  currentUses: number
  expiresAt?: string
  isActive: boolean
  createdAt: string
  usedAt?: string
}

// API 响应基础类型
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data: T
  code?: number
  timestamp?: string
}

// 分页响应类型
export interface PaginatedResponse<T = any> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}