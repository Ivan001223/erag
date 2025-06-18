<template>
  <div class="roles-list">
    <div class="page-header">
      <h1>角色管理</h1>
      <p>管理系统角色和权限配置</p>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索角色..."
          prefix-icon="Search"
          clearable
          @input="handleSearch"
        />
      </div>
      <div class="actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建角色
        </el-button>
      </div>
    </div>

    <div class="roles-table">
      <el-table
        :data="filteredRoles"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="角色名称" />
        <el-table-column prop="code" label="角色代码" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="permissions" label="权限数量">
          <template #default="{ row }">
            <el-tag>{{ row.permissions.length }} 个权限</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="userCount" label="用户数量" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" />
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button size="small" @click="handleViewPermissions(row)">
              查看权限
            </el-button>
            <el-button size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(row)"
              :disabled="row.code === 'admin'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 权限查看对话框 -->
    <el-dialog
      v-model="permissionDialogVisible"
      :title="`${selectedRole?.name} - 权限列表`"
      width="600px"
    >
      <div class="permissions-list">
        <el-tree
          :data="permissionTreeData"
          show-checkbox
          node-key="id"
          :default-checked-keys="selectedRole?.permissions || []"
          :props="{ children: 'children', label: 'name' }"
          disabled
        />
      </div>
      <template #footer>
        <el-button @click="permissionDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'

interface Role {
  id: number
  name: string
  code: string
  description: string
  permissions: string[]
  userCount: number
  status: 'active' | 'inactive'
  createdAt: string
}

interface Permission {
  id: string
  name: string
  children?: Permission[]
}

const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const roles = ref<Role[]>([])
const permissionDialogVisible = ref(false)
const selectedRole = ref<Role | null>(null)

const filteredRoles = computed(() => {
  if (!searchQuery.value) return roles.value
  return roles.value.filter(role => 
    role.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    role.code.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 权限树数据
const permissionTreeData = ref<Permission[]>([
  {
    id: 'user',
    name: '用户管理',
    children: [
      { id: 'user:read', name: '查看用户' },
      { id: 'user:create', name: '创建用户' },
      { id: 'user:update', name: '编辑用户' },
      { id: 'user:delete', name: '删除用户' }
    ]
  },
  {
    id: 'role',
    name: '角色管理',
    children: [
      { id: 'role:read', name: '查看角色' },
      { id: 'role:create', name: '创建角色' },
      { id: 'role:update', name: '编辑角色' },
      { id: 'role:delete', name: '删除角色' }
    ]
  },
  {
    id: 'knowledge',
    name: '知识管理',
    children: [
      { id: 'knowledge:read', name: '查看知识' },
      { id: 'knowledge:create', name: '创建知识' },
      { id: 'knowledge:update', name: '编辑知识' },
      { id: 'knowledge:delete', name: '删除知识' }
    ]
  }
])

const loadRoles = async () => {
  loading.value = true
  try {
    // TODO: 实现API调用
    // const response = await roleApi.getRoles({
    //   page: currentPage.value,
    //   size: pageSize.value,
    //   search: searchQuery.value
    // })
    
    // 模拟数据
    roles.value = [
      {
        id: 1,
        name: '超级管理员',
        code: 'admin',
        description: '系统超级管理员，拥有所有权限',
        permissions: ['user:read', 'user:create', 'user:update', 'user:delete', 'role:read', 'role:create', 'role:update', 'role:delete'],
        userCount: 1,
        status: 'active',
        createdAt: '2024-01-01 10:00:00'
      },
      {
        id: 2,
        name: '普通用户',
        code: 'user',
        description: '普通用户角色',
        permissions: ['knowledge:read'],
        userCount: 5,
        status: 'active',
        createdAt: '2024-01-02 10:00:00'
      },
      {
        id: 3,
        name: '知识管理员',
        code: 'knowledge_admin',
        description: '知识库管理员',
        permissions: ['knowledge:read', 'knowledge:create', 'knowledge:update', 'knowledge:delete'],
        userCount: 2,
        status: 'active',
        createdAt: '2024-01-03 10:00:00'
      }
    ]
    total.value = roles.value.length
  } catch (error) {
    ElMessage.error('加载角色列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadRoles()
}

const handleCreate = () => {
  // TODO: 导航到创建角色页面
  ElMessage.info('创建角色功能开发中')
}

const handleEdit = (role: Role) => {
  // TODO: 导航到编辑角色页面
  ElMessage.info(`编辑角色: ${role.name}`)
}

const handleViewPermissions = (role: Role) => {
  selectedRole.value = role
  permissionDialogVisible.value = true
}

const handleDelete = async (role: Role) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色 "${role.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // TODO: 实现删除API调用
    ElMessage.success('删除成功')
    loadRoles()
  } catch {
    // 用户取消删除
  }
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  loadRoles()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  loadRoles()
}

onMounted(() => {
  loadRoles()
})
</script>

<style scoped>
.roles-list {
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
  max-width: 400px;
}

.actions {
  display: flex;
  gap: 12px;
}

.roles-table {
  margin-bottom: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
}

.permissions-list {
  max-height: 400px;
  overflow-y: auto;
}
</style>