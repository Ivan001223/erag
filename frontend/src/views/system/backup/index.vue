<template>
  <div class="system-backup">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <h2>系统备份</h2>
          <p>管理系统数据备份和恢复</p>
        </div>
      </template>

      <!-- 备份操作区域 -->
      <div class="backup-actions">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card class="action-card">
              <template #header>
                <div class="action-header">
                  <el-icon size="20"><Upload /></el-icon>
                  <span>创建备份</span>
                </div>
              </template>
              <el-form :model="backupForm" label-width="100px">
                <el-form-item label="备份类型">
                  <el-radio-group v-model="backupForm.type">
                    <el-radio label="full">完整备份</el-radio>
                    <el-radio label="incremental">增量备份</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="备份范围">
                  <el-checkbox-group v-model="backupForm.scope">
                    <el-checkbox label="database">数据库</el-checkbox>
                    <el-checkbox label="files">文件系统</el-checkbox>
                    <el-checkbox label="config">配置文件</el-checkbox>
                    <el-checkbox label="logs">日志文件</el-checkbox>
                  </el-checkbox-group>
                </el-form-item>
                <el-form-item label="备份描述">
                  <el-input
                    v-model="backupForm.description"
                    type="textarea"
                    :rows="2"
                    placeholder="请输入备份描述"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    @click="createBackup"
                    :loading="creating"
                    :disabled="backupForm.scope.length === 0"
                  >
                    <el-icon><Upload /></el-icon>
                    开始备份
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="action-card">
              <template #header>
                <div class="action-header">
                  <el-icon size="20"><Download /></el-icon>
                  <span>恢复备份</span>
                </div>
              </template>
              <el-form :model="restoreForm" label-width="100px">
                <el-form-item label="选择备份">
                  <el-select v-model="restoreForm.backupId" placeholder="请选择要恢复的备份" style="width: 100%">
                    <el-option
                      v-for="backup in backups"
                      :key="backup.id"
                      :label="`${backup.name} (${backup.createTime})`"
                      :value="backup.id"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="恢复选项">
                  <el-checkbox-group v-model="restoreForm.options">
                    <el-checkbox label="overwrite">覆盖现有数据</el-checkbox>
                    <el-checkbox label="backup_current">备份当前数据</el-checkbox>
                  </el-checkbox-group>
                </el-form-item>
                <el-form-item label="确认密码">
                  <el-input
                    v-model="restoreForm.password"
                    type="password"
                    placeholder="请输入管理员密码确认"
                    show-password
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="danger"
                    @click="restoreBackup"
                    :loading="restoring"
                    :disabled="!restoreForm.backupId || !restoreForm.password"
                  >
                    <el-icon><Download /></el-icon>
                    开始恢复
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 备份进度 -->
      <div v-if="backupProgress.show" class="progress-section">
        <el-card class="progress-card">
          <template #header>
            <div class="progress-header">
              <span>{{ backupProgress.title }}</span>
              <el-button v-if="!backupProgress.completed" type="danger" size="small" @click="cancelBackup">
                取消
              </el-button>
            </div>
          </template>
          <div class="progress-content">
            <el-progress
              :percentage="backupProgress.percentage"
              :status="backupProgress.status"
              :stroke-width="8"
            />
            <div class="progress-info">
              <p>{{ backupProgress.message }}</p>
              <div class="progress-details">
                <span>已处理: {{ backupProgress.processed }}</span>
                <span>总计: {{ backupProgress.total }}</span>
                <span>速度: {{ backupProgress.speed }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 备份列表 -->
      <div class="backup-list">
        <el-card class="list-card">
          <template #header>
            <div class="list-header">
              <span>备份历史</span>
              <div class="header-actions">
                <el-button type="primary" size="small" @click="refreshBackups" :loading="loading">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
                <el-button type="danger" size="small" @click="cleanupBackups">
                  <el-icon><Delete /></el-icon>
                  清理过期备份
                </el-button>
              </div>
            </div>
          </template>
          <el-table :data="backups" v-loading="loading" stripe>
            <el-table-column prop="name" label="备份名称" width="200" />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.type === 'full' ? 'primary' : 'success'" size="small">
                  {{ row.type === 'full' ? '完整备份' : '增量备份' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="scope" label="备份范围" width="200">
              <template #default="{ row }">
                <el-tag v-for="item in row.scope" :key="item" size="small" style="margin-right: 5px">
                  {{ getScopeText(item) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="100">
              <template #default="{ row }">
                <span>{{ formatSize(row.size) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="创建时间" width="180" sortable />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  @click="downloadBackup(row)"
                  :disabled="row.status !== 'completed'"
                >
                  下载
                </el-button>
                <el-button
                  type="success"
                  size="small"
                  @click="selectForRestore(row)"
                  :disabled="row.status !== 'completed'"
                >
                  恢复
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  @click="deleteBackup(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- 自动备份设置 -->
      <div class="auto-backup">
        <el-card class="settings-card">
          <template #header>
            <span>自动备份设置</span>
          </template>
          <el-form :model="autoBackupSettings" label-width="120px">
            <el-form-item label="启用自动备份">
              <el-switch v-model="autoBackupSettings.enabled" />
            </el-form-item>
            <el-form-item label="备份频率" v-if="autoBackupSettings.enabled">
              <el-select v-model="autoBackupSettings.frequency">
                <el-option label="每日" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
              </el-select>
            </el-form-item>
            <el-form-item label="备份时间" v-if="autoBackupSettings.enabled">
              <el-time-picker
                v-model="autoBackupSettings.time"
                format="HH:mm"
                value-format="HH:mm"
              />
            </el-form-item>
            <el-form-item label="保留天数" v-if="autoBackupSettings.enabled">
              <el-input-number v-model="autoBackupSettings.retention" :min="1" :max="365" />
            </el-form-item>
            <el-form-item label="备份范围" v-if="autoBackupSettings.enabled">
              <el-checkbox-group v-model="autoBackupSettings.scope">
                <el-checkbox label="database">数据库</el-checkbox>
                <el-checkbox label="files">文件系统</el-checkbox>
                <el-checkbox label="config">配置文件</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveAutoBackupSettings">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload,
  Download,
  Refresh,
  Delete
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

// 接口定义
interface Backup {
  id: string
  name: string
  type: 'full' | 'incremental'
  scope: string[]
  size: number
  createTime: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  description: string
}

// 响应式数据
const loading = ref(false)
const creating = ref(false)
const restoring = ref(false)

// 备份表单
const backupForm = reactive<{
  type: 'full' | 'incremental';
  scope: string[];
  description: string;
}>({
  type: 'full',
  scope: ['database'],
  description: ''
})

// 恢复表单
const restoreForm = reactive({
  backupId: '',
  options: ['backup_current'],
  password: ''
})

// 备份进度
const backupProgress = reactive({
  show: false,
  title: '',
  percentage: 0,
  status: 'success' as 'success' | 'exception' | 'warning',
  message: '',
  processed: 0,
  total: 0,
  speed: '',
  completed: false
})

// 自动备份设置
const autoBackupSettings = reactive({
  enabled: false,
  frequency: 'daily',
  time: '02:00',
  retention: 30,
  scope: ['database', 'config']
})

// 备份列表
const backups = ref<Backup[]>([
  {
    id: '1',
    name: 'backup_20240115_full',
    type: 'full',
    scope: ['database', 'files', 'config'],
    size: 1024 * 1024 * 500, // 500MB
    createTime: '2024-01-15 02:00:00',
    status: 'completed',
    description: '每日自动完整备份'
  },
  {
    id: '2',
    name: 'backup_20240114_incremental',
    type: 'incremental',
    scope: ['database'],
    size: 1024 * 1024 * 50, // 50MB
    createTime: '2024-01-14 14:30:00',
    status: 'completed',
    description: '手动增量备份'
  },
  {
    id: '3',
    name: 'backup_20240113_full',
    type: 'full',
    scope: ['database', 'files'],
    size: 1024 * 1024 * 480, // 480MB
    createTime: '2024-01-13 02:00:00',
    status: 'failed',
    description: '自动备份失败'
  }
])

// 方法
const createBackup = async () => {
  creating.value = true
  backupProgress.show = true
  backupProgress.title = '正在创建备份'
  backupProgress.percentage = 0
  backupProgress.status = 'success'
  backupProgress.message = '准备备份...'
  backupProgress.completed = false
  
  try {
    // 模拟备份进度
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 500))
      backupProgress.percentage = i
      backupProgress.processed = Math.floor(i * 10)
      backupProgress.total = 1000
      backupProgress.speed = '15MB/s'
      
      if (i === 30) {
        backupProgress.message = '正在备份数据库...'
      } else if (i === 60) {
        backupProgress.message = '正在备份文件系统...'
      } else if (i === 90) {
        backupProgress.message = '正在压缩备份文件...'
      } else if (i === 100) {
        backupProgress.message = '备份完成'
        backupProgress.completed = true
      }
    }
    
    // 添加新备份到列表
    const newBackup: Backup = {
      id: Date.now().toString(),
      name: `backup_${dayjs().format('YYYYMMDD_HHmmss')}_${backupForm.type}`,
      type: backupForm.type,
      scope: [...backupForm.scope],
      size: Math.floor(Math.random() * 1024 * 1024 * 500),
      createTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      status: 'completed',
      description: backupForm.description || '手动备份'
    }
    
    backups.value.unshift(newBackup)
    ElMessage.success('备份创建成功')
    
    // 重置表单
    backupForm.description = ''
  } catch (error) {
    backupProgress.status = 'exception'
    backupProgress.message = '备份失败'
    ElMessage.error('备份创建失败')
  } finally {
    creating.value = false
  }
}

const restoreBackup = async () => {
  try {
    await ElMessageBox.confirm(
      '恢复备份将会影响当前系统数据，确定要继续吗？',
      '确认恢复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    restoring.value = true
    backupProgress.show = true
    backupProgress.title = '正在恢复备份'
    backupProgress.percentage = 0
    backupProgress.status = 'success'
    backupProgress.message = '准备恢复...'
    backupProgress.completed = false
    
    // 模拟恢复进度
    for (let i = 0; i <= 100; i += 20) {
      await new Promise(resolve => setTimeout(resolve, 800))
      backupProgress.percentage = i
      
      if (i === 20) {
        backupProgress.message = '正在解压备份文件...'
      } else if (i === 40) {
        backupProgress.message = '正在恢复数据库...'
      } else if (i === 60) {
        backupProgress.message = '正在恢复文件系统...'
      } else if (i === 80) {
        backupProgress.message = '正在更新配置...'
      } else if (i === 100) {
        backupProgress.message = '恢复完成'
        backupProgress.completed = true
      }
    }
    
    ElMessage.success('备份恢复成功')
    restoreForm.backupId = ''
    restoreForm.password = ''
  } catch {
    // 用户取消
  } finally {
    restoring.value = false
  }
}

const cancelBackup = () => {
  backupProgress.show = false
  creating.value = false
  restoring.value = false
  ElMessage.info('操作已取消')
}

const refreshBackups = async () => {
  loading.value = true
  try {
    // 这里应该调用API刷新备份列表
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('备份列表已刷新')
  } catch (error) {
    ElMessage.error('刷新失败')
  } finally {
    loading.value = false
  }
}

const cleanupBackups = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清理过期备份吗？此操作不可恢复。',
      '确认清理',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里应该调用API清理过期备份
    ElMessage.success('过期备份已清理')
  } catch {
    // 用户取消
  }
}

const downloadBackup = (backup: Backup) => {
  // 这里应该调用API下载备份文件
  ElMessage.success(`开始下载 ${backup.name}`)
}

const selectForRestore = (backup: Backup) => {
  restoreForm.backupId = backup.id
  ElMessage.info(`已选择备份: ${backup.name}`)
}

const deleteBackup = async (backup: Backup) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除备份 "${backup.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const index = backups.value.findIndex(b => b.id === backup.id)
    if (index > -1) {
      backups.value.splice(index, 1)
      ElMessage.success('备份已删除')
    }
  } catch {
    // 用户取消
  }
}

const saveAutoBackupSettings = () => {
  // 这里应该调用API保存自动备份设置
  ElMessage.success('自动备份设置已保存')
}

const getScopeText = (scope: string) => {
  const texts: Record<string, string> = {
    database: '数据库',
    files: '文件系统',
    config: '配置文件',
    logs: '日志文件'
  }
  return texts[scope] || scope
}

const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '等待中',
    running: '进行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || '未知'
}

// 生命周期
onMounted(() => {
  // 加载自动备份设置
  console.log('加载备份页面')
})
</script>

<style scoped lang="scss">
.system-backup {
  padding: 20px;

  .page-card {
    .card-header {
      h2 {
        margin: 0 0 8px 0;
        color: #303133;
        font-size: 20px;
        font-weight: 600;
      }

      p {
        margin: 0;
        color: #909399;
        font-size: 14px;
      }
    }
  }

  .backup-actions {
    margin: 20px 0;

    .action-card {
      height: 100%;

      .action-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
      }
    }
  }

  .progress-section {
    margin: 20px 0;

    .progress-card {
      .progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .progress-content {
        .progress-info {
          margin-top: 15px;

          p {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #606266;
          }

          .progress-details {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #909399;
          }
        }
      }
    }
  }

  .backup-list {
    margin: 20px 0;

    .list-card {
      .list-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .header-actions {
          display: flex;
          gap: 10px;
        }
      }
    }
  }

  .auto-backup {
    margin: 20px 0;

    .settings-card {
      max-width: 600px;
    }
  }
}

:deep(.el-checkbox-group) {
  .el-checkbox {
    margin-right: 15px;
    margin-bottom: 8px;
  }
}

:deep(.el-radio-group) {
  .el-radio {
    margin-right: 15px;
  }
}
</style>