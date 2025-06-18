<template>
  <div class="departments-list">
    <div class="page-header">
      <h1>部门管理</h1>
      <p>管理组织架构和部门信息</p>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索部门..."
          prefix-icon="Search"
          clearable
          @input="handleSearch"
        />
      </div>
      <div class="actions">
        <el-button @click="expandAll">
          <el-icon><Expand /></el-icon>
          展开全部
        </el-button>
        <el-button @click="collapseAll">
          <el-icon><Fold /></el-icon>
          收起全部
        </el-button>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建部门
        </el-button>
      </div>
    </div>

    <div class="departments-tree">
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="treeProps"
        node-key="id"
        :expand-on-click-node="false"
        :default-expand-all="false"
        v-loading="loading"
        draggable
        @node-drop="handleNodeDrop"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <div class="node-content">
              <el-icon class="node-icon">
                <OfficeBuilding v-if="data.level === 1" />
                <Collection v-else-if="data.level === 2" />
                <User v-else />
              </el-icon>
              <span class="node-label">{{ data.name }}</span>
              <el-tag size="small" class="level-tag">
                {{ getLevelText(data.level) }}
              </el-tag>
              <span class="node-info">
                {{ data.userCount }} 人
              </span>
            </div>
            <div class="node-actions">
              <el-tag
                :type="data.status === 'active' ? 'success' : 'danger'"
                size="small"
              >
                {{ data.status === 'active' ? '启用' : '禁用' }}
              </el-tag>
              <el-button
                :size="'small'"
                type="primary"
                link
                @click="handleViewUsers(data)"
              >
                查看成员
              </el-button>
              <el-button
                :size="'small'"
                type="primary"
                link
                @click="handleEdit(data)"
              >
                编辑
              </el-button>
              <el-button
                :size="'small'"
                type="success"
                link
                @click="handleAddChild(data)"
              >
                添加子部门
              </el-button>
              <el-button
                size="small"
                type="danger"
                link
                @click="handleDelete(data)"
                :disabled="data.children && data.children.length > 0"
              >
                删除
              </el-button>
            </div>
          </div>
        </template>
      </el-tree>
    </div>

    <!-- 部门成员对话框 -->
    <el-dialog
      v-model="usersDialogVisible"
      :title="`${selectedDepartment?.name} - 部门成员`"
      width="800px"
    >
      <div class="users-list">
        <el-table
          :data="departmentUsers"
          v-loading="usersLoading"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="email" label="邮箱" />
          <el-table-column prop="role" label="角色" />
          <el-table-column prop="position" label="职位" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
                {{ row.status === 'active' ? '在职' : '离职' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" @click="handleTransferUser(row)">
                调动
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="handleRemoveUser(row)"
              >
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="usersDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleAddUser">
          添加成员
        </el-button>
      </template>
    </el-dialog>

    <!-- 部门详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="selectedDepartment?.name"
      width="600px"
    >
      <div class="department-detail" v-if="selectedDepartment">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="部门名称">
            {{ selectedDepartment.name }}
          </el-descriptions-item>
          <el-descriptions-item label="部门代码">
            {{ selectedDepartment.code }}
          </el-descriptions-item>
          <el-descriptions-item label="部门级别">
            {{ getLevelText(selectedDepartment.level) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedDepartment.status === 'active' ? 'success' : 'danger'">
              {{ selectedDepartment.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="负责人">
            {{ selectedDepartment.manager || '暂无' }}
          </el-descriptions-item>
          <el-descriptions-item label="人员数量">
            {{ selectedDepartment.userCount }} 人
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ selectedDepartment.description || '暂无描述' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ selectedDepartment.createdAt }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ selectedDepartment.updatedAt }}
          </el-descriptions-item>
        </el-descriptions>
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
import { 
  Plus, 
  Search, 
  Expand, 
  Fold, 
  OfficeBuilding, 
  Collection, 
  User 
} from '@element-plus/icons-vue'

interface Department {
  id: string
  name: string
  code: string
  level: number
  parentId?: string
  manager?: string
  userCount: number
  status: 'active' | 'inactive'
  description?: string
  createdAt: string
  updatedAt: string
  children?: Department[]
}

interface DepartmentUser {
  id: string
  username: string
  email: string
  role: string
  position: string
  status: 'active' | 'inactive'
}

const loading = ref(false)
const usersLoading = ref(false)
const searchQuery = ref('')
const usersDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const selectedDepartment = ref<Department | null>(null)
const departmentUsers = ref<DepartmentUser[]>([])
const treeRef = ref()

const treeProps = {
  children: 'children',
  label: 'name'
}

const departments = ref<Department[]>([])

const treeData = computed(() => {
  if (!searchQuery.value) return departments.value
  
  // 递归过滤部门树
  const filterTree = (nodes: Department[]): Department[] => {
    return nodes.filter(node => {
      const matchesSearch = node.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                           node.code.toLowerCase().includes(searchQuery.value.toLowerCase())
      
      if (node.children) {
        const filteredChildren = filterTree(node.children)
        if (filteredChildren.length > 0) {
          return { ...node, children: filteredChildren }
        }
      }
      
      return matchesSearch
    })
  }
  
  return filterTree(departments.value)
})

const getLevelText = (level: number): string => {
  const levelMap: Record<number, string> = {
    1: '一级部门',
    2: '二级部门',
    3: '三级部门',
    4: '四级部门'
  }
  return levelMap[level] || `${level}级部门`
}

const loadDepartments = async () => {
  loading.value = true
  try {
    // TODO: 实现API调用
    // const response = await departmentApi.getDepartments()
    
    // 模拟数据
    departments.value = [
      {
        id: '1',
        name: '技术部',
        code: 'TECH',
        level: 1,
        manager: '张三',
        userCount: 15,
        status: 'active',
        description: '负责公司技术研发工作',
        createdAt: '2024-01-01 10:00:00',
        updatedAt: '2024-01-01 10:00:00',
        children: [
          {
            id: '11',
            name: '前端开发组',
            code: 'TECH_FE',
            level: 2,
            parentId: '1',
            manager: '李四',
            userCount: 6,
            status: 'active',
            description: '负责前端开发工作',
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          },
          {
            id: '12',
            name: '后端开发组',
            code: 'TECH_BE',
            level: 2,
            parentId: '1',
            manager: '王五',
            userCount: 8,
            status: 'active',
            description: '负责后端开发工作',
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          },
          {
            id: '13',
            name: '测试组',
            code: 'TECH_QA',
            level: 2,
            parentId: '1',
            manager: '赵六',
            userCount: 1,
            status: 'active',
            description: '负责软件测试工作',
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          }
        ]
      },
      {
        id: '2',
        name: '产品部',
        code: 'PRODUCT',
        level: 1,
        manager: '钱七',
        userCount: 8,
        status: 'active',
        description: '负责产品设计和规划',
        createdAt: '2024-01-01 10:00:00',
        updatedAt: '2024-01-01 10:00:00',
        children: [
          {
            id: '21',
            name: '产品设计组',
            code: 'PRODUCT_DESIGN',
            level: 2,
            parentId: '2',
            manager: '孙八',
            userCount: 4,
            status: 'active',
            description: '负责产品UI/UX设计',
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          },
          {
            id: '22',
            name: '产品运营组',
            code: 'PRODUCT_OPS',
            level: 2,
            parentId: '2',
            manager: '周九',
            userCount: 4,
            status: 'active',
            description: '负责产品运营推广',
            createdAt: '2024-01-01 10:00:00',
            updatedAt: '2024-01-01 10:00:00'
          }
        ]
      }
    ]
  } catch (error) {
    ElMessage.error('加载部门列表失败')
  } finally {
    loading.value = false
  }
}

const loadDepartmentUsers = async (departmentId: string) => {
  usersLoading.value = true
  try {
    // TODO: 实现API调用
    // const response = await departmentApi.getDepartmentUsers(departmentId)
    
    // 模拟数据
    departmentUsers.value = [
      {
        id: '1',
        username: 'user1',
        email: 'user1@example.com',
        role: '开发工程师',
        position: '高级前端工程师',
        status: 'active'
      },
      {
        id: '2',
        username: 'user2',
        email: 'user2@example.com',
        role: '开发工程师',
        position: '前端工程师',
        status: 'active'
      }
    ]
  } catch (error) {
    ElMessage.error('加载部门成员失败')
  } finally {
    usersLoading.value = false
  }
}

const handleSearch = () => {
  // 搜索逻辑已在计算属性中处理
}

const expandAll = () => {
  // 展开所有节点
  const expandAllNodes = (nodes: Department[]) => {
    nodes.forEach(node => {
      treeRef.value?.setExpanded(node.id, true)
      if (node.children) {
        expandAllNodes(node.children)
      }
    })
  }
  expandAllNodes(departments.value)
}

const collapseAll = () => {
  // 收起所有节点
  const collapseAllNodes = (nodes: Department[]) => {
    nodes.forEach(node => {
      treeRef.value?.setExpanded(node.id, false)
      if (node.children) {
        collapseAllNodes(node.children)
      }
    })
  }
  collapseAllNodes(departments.value)
}

const handleCreate = () => {
  // TODO: 导航到创建部门页面
  ElMessage.info('创建部门功能开发中')
}

const handleEdit = (department: Department) => {
  selectedDepartment.value = department
  detailDialogVisible.value = true
}

const handleAddChild = (department: Department) => {
  // TODO: 导航到创建子部门页面
  ElMessage.info(`为 ${department.name} 添加子部门功能开发中`)
}

const handleViewUsers = (department: Department) => {
  selectedDepartment.value = department
  usersDialogVisible.value = true
  loadDepartmentUsers(department.id)
}

const handleDelete = async (department: Department) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除部门 "${department.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // TODO: 实现删除API调用
    ElMessage.success('删除成功')
    loadDepartments()
  } catch {
    // 用户取消删除
  }
}

const handleNodeDrop = (draggingNode: any, dropNode: any, dropType: string) => {
  // TODO: 实现部门拖拽排序
  ElMessage.success('部门结构调整成功')
}

const handleAddUser = () => {
  // TODO: 实现添加部门成员
  ElMessage.info('添加部门成员功能开发中')
}

const handleTransferUser = (user: DepartmentUser) => {
  // TODO: 实现用户调动
  ElMessage.info(`调动用户 ${user.username} 功能开发中`)
}

const handleRemoveUser = async (user: DepartmentUser) => {
  try {
    await ElMessageBox.confirm(
      `确定要将 "${user.username}" 从当前部门移除吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // TODO: 实现移除API调用
    ElMessage.success('移除成功')
    loadDepartmentUsers(selectedDepartment.value!.id)
  } catch {
    // 用户取消移除
  }
}

onMounted(() => {
  loadDepartments()
})
</script>

<style scoped>
.departments-list {
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

.actions {
  display: flex;
  gap: 12px;
}

.departments-tree {
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
  gap: 12px;
  flex: 1;
}

.node-icon {
  color: #6b7280;
}

.node-label {
  font-weight: 500;
  color: #1f2937;
  min-width: 120px;
}

.level-tag {
  background: #f3f4f6;
  color: #6b7280;
}

.node-info {
  color: #6b7280;
  font-size: 14px;
}

.node-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.users-list {
  margin-bottom: 16px;
}

.department-detail {
  margin-bottom: 16px;
}
</style>