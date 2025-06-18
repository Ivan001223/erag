<template>
  <div class="permissions-list">
    <div class="page-header">
      <h1>权限管理</h1>
      <p>管理系统权限和访问控制</p>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索权限..."
          prefix-icon="Search"
          clearable
          @input="handleSearch"
        />
      </div>
      <div class="filters">
        <el-select
          v-model="selectedModule"
          placeholder="选择模块"
          clearable
          @change="handleModuleChange"
        >
          <el-option
            v-for="module in modules"
            :key="module.value"
            :label="module.label"
            :value="module.value"
          />
        </el-select>
      </div>
      <div class="actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建权限
        </el-button>
      </div>
    </div>

    <div class="permissions-tree">
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="treeProps"
        node-key="id"
        :expand-on-click-node="false"
        :default-expand-all="true"
        v-loading="loading"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <div class="node-content">
              <span class="node-label">{{ data.name }}</span>
              <span class="node-code">{{ data.code }}</span>
              <span class="node-description">{{ data.description }}</span>
            </div>
            <div class="node-actions">
              <el-tag
                :type="data.status === 'active' ? 'success' : 'danger'"
                size="small"
              >
                {{ data.status === 'active' ? '启用' : '禁用' }}
              </el-tag>
              <el-button
                size="small"
                type="primary"
                link
                @click="handleEdit(data)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                type="danger"
                link
                @click="handleDelete(data)"
                :disabled="data.isSystem"
              >
                删除
              </el-button>
            </div>
          </div>
        </template>
      </el-tree>
    </div>

    <!-- 权限详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="selectedPermission?.name"
      width="600px"
    >
      <div class="permission-detail" v-if="selectedPermission">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="权限名称">
            {{ selectedPermission.name }}
          </el-descriptions-item>
          <el-descriptions-item label="权限代码">
            {{ selectedPermission.code }}
          </el-descriptions-item>
          <el-descriptions-item label="所属模块">
            {{ selectedPermission.module }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedPermission.status === 'active' ? 'success' : 'danger'">
              {{ selectedPermission.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ selectedPermission.description }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ selectedPermission.createdAt }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ selectedPermission.updatedAt }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="related-roles" v-if="selectedPermission.roles?.length">
          <h4>关联角色</h4>
          <el-tag
            v-for="role in selectedPermission.roles"
            :key="role"
            style="margin-right: 8px; margin-bottom: 8px;"
          >
            {{ role }}
          </el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'

interface Permission {
  id: string
  name: string
  code: string
  description: string
  module: string
  status: 'active' | 'inactive'
  isSystem: boolean
  roles?: string[]
  createdAt: string
  updatedAt: string
  children?: Permission[]
}

const loading = ref(false)
const searchQuery = ref('')
const selectedModule = ref('')
const detailDialogVisible = ref(false)
const selectedPermission = ref<Permission | null>(null)
const treeRef = ref()

const modules = ref([
  { label: '用户管理', value: 'user' },
  { label: '角色管理', value: 'role' },
  { label: '权限管理', value: 'permission' },
  { label: '知识管理', value: 'knowledge' },
  { label: 'ETL管理', value: 'etl' },
  { label: '系统管理', value: 'system' }
])

const treeProps = {
  children: 'children',
  label: 'name'
}

const permissions = ref<Permission[]>([])

const treeData = computed(() => {
  let data = permissions.value
  
  // 按模块过滤
  if (selectedModule.value) {
    data = data.filter(item => item.module === selectedModule.value)
  }
  
  // 按搜索关键词过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    data = data.filter(item => 
      item.name.toLowerCase().includes(query) ||
      item.code.toLowerCase().includes(query) ||
      item.description.toLowerCase().includes(query)
    )
  }
  
  return data
})

const loadPermissions = async () => {
  loading.value = true
  try {
    // TODO: 实现API调用
    // const response = await permissionApi.getPermissions()
    
    // 模拟数据
    permissions.value = [
      {
        id: 'user',
        name: '用户管理',
        code: 'user',
        description: '用户管理模块权限',
        module: 'user',
        status: 'active',
        isSystem: true,
        roles: ['超级管理员'],
        createdAt: '2024-01-01 10:00:00',
        updatedAt: '2024-01-01 10:00:00',
        children: [
          {
            id: 'user:read',
            name: '查看用户',
            code: 'user:read',
            description: '查看用户列表和详情',
            module: 'user',
            status: 'active',
            isSystem: true,
            roles: ['超级管理员', '用户管理员'],
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          },
          {
            id: 'user:create',
            name: '创建用户',
            code: 'user:create',
            description: '创建新用户账户',
            module: 'user',
            status: 'active',
            isSystem: true,
            roles: ['超级管理员'],
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          },
          {
            id: 'user:update',
            name: '编辑用户',
            code: 'user:update',
            description: '编辑用户信息',
            module: 'user',
            status: 'active',
            isSystem: true,
            roles: ['超级管理员'],
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          },
          {
            id: 'user:delete',
            name: '删除用户',
            code: 'user:delete',
            description: '删除用户账户',
            module: 'user',
            status: 'active',
            isSystem: true,
            roles: ['超级管理员'],
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          }
        ]
      },
      {
        id: 'knowledge',
        name: '知识管理',
        code: 'knowledge',
        description: '知识库管理模块权限',
        module: 'knowledge',
        status: 'active',
        isSystem: true,
        roles: ['超级管理员', '知识管理员'],
        createdAt: '2024-01-01 10:00:00',
        updatedAt: '2024-01-01 10:00:00',
        children: [
          {
            id: 'knowledge:read',
            name: '查看知识',
            code: 'knowledge:read',
            description: '查看知识库内容',
            module: 'knowledge',
            status: 'active',
            isSystem: true,
            roles: ['超级管理员', '知识管理员', '普通用户'],
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          },
          {
            id: 'knowledge:create',
            name: '创建知识',
            code: 'knowledge:create',
            description: '创建新的知识条目',
            module: 'knowledge',
            status: 'active',
            isSystem: true,
            roles: ['超级管理员', '知识管理员'],
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          }
        ]
      }
    ]
  } catch (error) {
    ElMessage.error('加载权限列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  // 搜索逻辑已在计算属性中处理
}

const handleModuleChange = () => {
  // 模块过滤逻辑已在计算属性中处理
}

const handleCreate = () => {
  // TODO: 导航到创建权限页面
  ElMessage.info('创建权限功能开发中')
}

const handleEdit = (permission: Permission) => {
  selectedPermission.value = permission
  detailDialogVisible.value = true
}

const handleDelete = async (permission: Permission) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除权限 "${permission.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // TODO: 实现删除API调用
    ElMessage.success('删除成功')
    loadPermissions()
  } catch {
    // 用户取消删除
  }
}

onMounted(() => {
  loadPermissions()
})
</script>

<style scoped>
.permissions-list {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.page-header p {
  margin: 0;
  color: #6b7280;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 16px;
}

.search-box {
  flex: 1;
  max-width: 300px;
}

.filters {
  display: flex;
  gap: 12px;
}

.actions {
  display: flex;
  gap: 12px;
}

.permissions-tree {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.node-label {
  font-weight: 500;
  color: #1f2937;
  min-width: 120px;
}

.node-code {
  font-family: 'Monaco', 'Menlo', monospace;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #6b7280;
  min-width: 150px;
}

.node-description {
  color: #6b7280;
  font-size: 14px;
  flex: 1;
}

.node-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.permission-detail {
  margin-bottom: 16px;
}

.related-roles {
  margin-top: 20px;
}

.related-roles h4 {
  margin: 0 0 12px 0;
  color: #1f2937;
}
</style>