import Request from '@/utils/request'
import type {
  LoginForm,
  RegisterForm,
  ForgotPasswordForm,
  ResetPasswordForm,
  ChangePasswordForm,
  UserProfile,
  UserListQuery,
  UserListResponse,
  LoginResponse,
  ApiResponse,
  PaginatedResponse
} from '@/types'

/**
 * 用户认证相关API
 */

/**
 * 用户登录
 * @param data 登录表单数据
 * @returns 登录响应
 */
export const login = (data: LoginForm): Promise<ApiResponse<LoginResponse>> => {
  return Request.post('/auth/login', data)
}

/**
 * 用户注册
 * @param data 注册表单数据
 * @returns 注册响应
 */
export const register = (data: RegisterForm): Promise<ApiResponse<{ message: string }>> => {
  return Request.post('/auth/register', data)
}

/**
 * 用户登出
 * @returns 登出响应
 */
export const logout = (): Promise<ApiResponse<{ message: string }>> => {
  return Request.post('/auth/logout')
}

/**
 * 刷新Token
 * @param refreshToken 刷新令牌
 * @returns 新的Token信息
 */
export const refreshToken = (refreshToken: string): Promise<ApiResponse<LoginResponse>> => {
  return Request.post('/auth/refresh', { refreshToken })
}

/**
 * 忘记密码
 * @param data 忘记密码表单数据
 * @returns 响应
 */
export const forgotPassword = (data: ForgotPasswordForm): Promise<ApiResponse<{ message: string }>> => {
  return Request.post('/auth/forgot-password', data)
}

/**
 * 重置密码
 * @param data 重置密码表单数据
 * @returns 响应
 */
export const resetPassword = (data: ResetPasswordForm): Promise<ApiResponse<{ message: string }>> => {
  return Request.post('/auth/reset-password', data)
}

/**
 * 修改密码
 * @param data 修改密码表单数据
 * @returns 响应
 */
export const changePassword = (data: ChangePasswordForm): Promise<ApiResponse<{ message: string }>> => {
  return Request.post('/auth/change-password', data)
}

/**
 * 验证Token有效性
 * @returns 验证结果
 */
export const validateToken = (): Promise<ApiResponse<{ valid: boolean }>> => {
  return Request.get('/auth/validate')
}

/**
 * 用户信息相关API
 */

/**
 * 获取当前用户信息
 * @returns 用户信息
 */
export const getUserInfo = (): Promise<ApiResponse<UserProfile>> => {
  return Request.get('/user/profile')
}

/**
 * 更新用户信息
 * @param data 用户信息
 * @returns 更新响应
 */
export const updateUserInfo = (data: Partial<UserProfile>): Promise<ApiResponse<UserProfile>> => {
  return Request.put('/user/profile', data)
}

/**
 * 上传用户头像
 * @param file 头像文件
 * @returns 上传响应
 */
export const uploadAvatar = (file: File): Promise<ApiResponse<{ avatarUrl: string }>> => {
  const formData = new FormData()
  formData.append('avatar', file)
  return Request.post('/user/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 删除用户头像
 * @returns 删除响应
 */
export const deleteAvatar = (): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete('/user/avatar')
}

/**
 * 获取用户偏好设置
 * @returns 偏好设置
 */
export const getUserPreferences = (): Promise<ApiResponse<Record<string, any>>> => {
  return Request.get('/user/preferences')
}

/**
 * 更新用户偏好设置
 * @param preferences 偏好设置
 * @returns 更新响应
 */
export const updateUserPreferences = (preferences: Record<string, any>): Promise<ApiResponse<Record<string, any>>> => {
  return Request.put('/user/preferences', preferences)
}

/**
 * 获取用户通知设置
 * @returns 通知设置
 */
export const getNotificationSettings = (): Promise<ApiResponse<Record<string, boolean>>> => {
  return Request.get('/user/notifications')
}

/**
 * 更新用户通知设置
 * @param settings 通知设置
 * @returns 更新响应
 */
export const updateNotificationSettings = (settings: Record<string, boolean>): Promise<ApiResponse<Record<string, boolean>>> => {
  return Request.put('/user/notifications', settings)
}

/**
 * 获取用户隐私设置
 * @returns 隐私设置
 */
export const getPrivacySettings = (): Promise<ApiResponse<Record<string, any>>> => {
  return Request.get('/user/privacy')
}

/**
 * 更新用户隐私设置
 * @param settings 隐私设置
 * @returns 更新响应
 */
export const updatePrivacySettings = (settings: Record<string, any>): Promise<ApiResponse<Record<string, any>>> => {
  return Request.put('/user/privacy', settings)
}

/**
 * 用户管理相关API（管理员功能）
 */

/**
 * 获取用户列表
 * @param params 查询参数
 * @returns 用户列表
 */
export const getUserList = (params: UserListQuery): Promise<PaginatedResponse<UserListResponse>> => {
  return Request.get<PaginatedResponse<UserListResponse>>('/admin/users', { params }).then(response => response.data)
}

/**
 * 获取用户详情
 * @param userId 用户ID
 * @returns 用户详情
 */
export const getUserDetail = (userId: string): Promise<ApiResponse<UserProfile>> => {
  return Request.get(`/admin/users/${userId}`)
}

/**
 * 创建用户
 * @param data 用户数据
 * @returns 创建响应
 */
export const createUser = (data: Omit<UserProfile, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<UserProfile>> => {
  return Request.post('/admin/users', data)
}

/**
 * 更新用户
 * @param userId 用户ID
 * @param data 用户数据
 * @returns 更新响应
 */
export const updateUser = (userId: string, data: Partial<UserProfile>): Promise<ApiResponse<UserProfile>> => {
  return Request.put(`/admin/users/${userId}`, data)
}

/**
 * 删除用户
 * @param userId 用户ID
 * @returns 删除响应
 */
export const deleteUser = (userId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/admin/users/${userId}`)
}

/**
 * 批量删除用户
 * @param userIds 用户ID数组
 * @returns 删除响应
 */
export const batchDeleteUsers = (userIds: string[]): Promise<ApiResponse<{ message: string; deletedCount: number }>> => {
  return Request.post('/admin/users/batch-delete', { userIds })
}

/**
 * 启用/禁用用户
 * @param userId 用户ID
 * @param enabled 是否启用
 * @returns 响应
 */
export const toggleUserStatus = (userId: string, enabled: boolean): Promise<ApiResponse<{ message: string }>> => {
  return Request.patch(`/admin/users/${userId}/status`, { enabled })
}

/**
 * 重置用户密码
 * @param userId 用户ID
 * @param newPassword 新密码
 * @returns 响应
 */
export const resetUserPassword = (userId: string, newPassword: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.post(`/admin/users/${userId}/reset-password`, { newPassword })
}

/**
 * 分配用户角色
 * @param userId 用户ID
 * @param roleIds 角色ID数组
 * @returns 响应
 */
export const assignUserRoles = (userId: string, roleIds: string[]): Promise<ApiResponse<{ message: string }>> => {
  return Request.post(`/admin/users/${userId}/roles`, { roleIds })
}

/**
 * 移除用户角色
 * @param userId 用户ID
 * @param roleIds 角色ID数组
 * @returns 响应
 */
export const removeUserRoles = (userId: string, roleIds: string[]): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/admin/users/${userId}/roles`, { data: { roleIds } })
}

/**
 * 获取用户权限
 * @param userId 用户ID
 * @returns 用户权限
 */
export const getUserPermissions = (userId: string): Promise<ApiResponse<string[]>> => {
  return Request.get(`/admin/users/${userId}/permissions`)
}

/**
 * 分配用户权限
 * @param userId 用户ID
 * @param permissions 权限数组
 * @returns 响应
 */
export const assignUserPermissions = (userId: string, permissions: string[]): Promise<ApiResponse<{ message: string }>> => {
  return Request.post(`/admin/users/${userId}/permissions`, { permissions })
}

/**
 * 移除用户权限
 * @param userId 用户ID
 * @param permissions 权限数组
 * @returns 响应
 */
export const removeUserPermissions = (userId: string, permissions: string[]): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/admin/users/${userId}/permissions`, { data: { permissions } })
}

/**
 * 用户活动相关API
 */

/**
 * 获取用户活动日志
 * @param userId 用户ID
 * @param params 查询参数
 * @returns 活动日志
 */
export const getUserActivityLogs = (
  userId: string,
  params: {
    page?: number
    pageSize?: number
    startDate?: string
    endDate?: string
    action?: string
  } = {}
): Promise<PaginatedResponse<any>> => {
  return Request.get<PaginatedResponse<any>>(`/admin/users/${userId}/activities`, { params }).then(response => response.data)
}

/**
 * 获取用户登录历史
 * @param userId 用户ID
 * @param params 查询参数
 * @returns 登录历史
 */
export const getUserLoginHistory = (
  userId: string,
  params: {
    page?: number
    pageSize?: number
    startDate?: string
    endDate?: string
  } = {}
): Promise<PaginatedResponse<any>> => {
  return Request.get<PaginatedResponse<any>>(`/admin/users/${userId}/login-history`, { params }).then(response => response.data)
}

/**
 * 获取用户会话信息
 * @param userId 用户ID
 * @returns 会话信息
 */
export const getUserSessions = (userId: string): Promise<ApiResponse<any[]>> => {
  return Request.get(`/admin/users/${userId}/sessions`)
}

/**
 * 终止用户会话
 * @param userId 用户ID
 * @param sessionId 会话ID
 * @returns 响应
 */
export const terminateUserSession = (userId: string, sessionId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/admin/users/${userId}/sessions/${sessionId}`)
}

/**
 * 终止用户所有会话
 * @param userId 用户ID
 * @returns 响应
 */
export const terminateAllUserSessions = (userId: string): Promise<ApiResponse<{ message: string }>> => {
  return Request.delete(`/admin/users/${userId}/sessions`)
}

/**
 * 用户统计相关API
 */

/**
 * 获取用户统计信息
 * @returns 统计信息
 */
export const getUserStats = (): Promise<ApiResponse<{
  totalUsers: number
  activeUsers: number
  newUsersToday: number
  newUsersThisWeek: number
  newUsersThisMonth: number
  usersByRole: Record<string, number>
  usersByStatus: Record<string, number>
}>> => {
  return Request.get('/admin/users/stats')
}

/**
 * 获取用户增长趋势
 * @param params 查询参数
 * @returns 增长趋势数据
 */
export const getUserGrowthTrend = (params: {
  startDate: string
  endDate: string
  granularity: 'day' | 'week' | 'month'
}): Promise<ApiResponse<Array<{
  date: string
  count: number
  cumulative: number
}>>> => {
  return Request.get('/admin/users/growth-trend', { params })
}

/**
 * 获取用户活跃度统计
 * @param params 查询参数
 * @returns 活跃度统计
 */
export const getUserActivityStats = (params: {
  startDate: string
  endDate: string
}): Promise<ApiResponse<{
  dailyActiveUsers: number
  weeklyActiveUsers: number
  monthlyActiveUsers: number
  averageSessionDuration: number
  topActiveUsers: Array<{
    userId: string
    username: string
    activityCount: number
  }>
}>> => {
  return Request.get('/admin/users/activity-stats', { params })
}

/**
 * 导入/导出相关API
 */

/**
 * 导出用户数据
 * @param params 导出参数
 * @returns 导出文件
 */
export const exportUsers = (params: {
  format: 'csv' | 'excel' | 'json'
  filters?: UserListQuery
}): Promise<Blob> => {
  return Request.get('/admin/users/export', {
    params,
    responseType: 'blob'
  }).then(response => response.data as Blob)
}

/**
 * 导入用户数据
 * @param file 导入文件
 * @param options 导入选项
 * @returns 导入结果
 */
export const importUsers = (
  file: File,
  options: {
    skipHeader?: boolean
    updateExisting?: boolean
    sendWelcomeEmail?: boolean
  } = {}
): Promise<ApiResponse<{
  total: number
  success: number
  failed: number
  errors: Array<{
    row: number
    message: string
  }>
}>> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('options', JSON.stringify(options))
  
  return Request.post('/admin/users/import', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 获取导入模板
 * @param format 模板格式
 * @returns 模板文件
 */
export const getUserImportTemplate = (format: 'csv' | 'excel'): Promise<Blob> => {
  return Request.get(`/admin/users/import-template`, {
    params: { format },
    responseType: 'blob'
  }).then(response => response.data as Blob)
}

// 导出用户API对象
export const userApi = {
  // 认证相关
  login,
  register,
  logout,
  refreshToken,
  forgotPassword,
  resetPassword,
  changePassword,
  validateToken,
  
  // 用户信息相关
  getUserInfo,
  updateUserInfo,
  uploadAvatar,
  deleteAvatar,
  
  // 用户设置相关
  getUserPreferences,
  updateUserPreferences,
  getNotificationSettings,
  updateNotificationSettings,
  getPrivacySettings,
  updatePrivacySettings,
  
  // 管理员用户管理
  getUserList,
  getUserDetail,
  createUser,
  updateUser,
  deleteUser,
  batchDeleteUsers,
  toggleUserStatus,
  resetUserPassword,
  
  // 角色和权限管理
  assignUserRoles,
  removeUserRoles,
  getUserPermissions,
  assignUserPermissions,
  removeUserPermissions,
  
  // 用户活动和会话
  getUserActivityLogs,
  getUserLoginHistory,
  getUserSessions,
  terminateUserSession,
  terminateAllUserSessions,
  
  // 统计和分析
  getUserStats,
  getUserGrowthTrend,
  getUserActivityStats,
  
  // 导入导出
  exportUsers,
  importUsers,
  getUserImportTemplate
}