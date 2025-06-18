<template>
  <div class="dev-components">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <h2>组件展示</h2>
          <p>开发环境下的组件库展示和测试</p>
        </div>
      </template>

      <!-- 组件分类 -->
      <div class="component-categories">
        <el-tabs v-model="activeTab" type="border-card">
          <!-- 基础组件 -->
          <el-tab-pane label="基础组件" name="basic">
            <div class="component-section">
              <h3>按钮组件</h3>
              <div class="demo-block">
                <el-button>默认按钮</el-button>
                <el-button type="primary">主要按钮</el-button>
                <el-button type="success">成功按钮</el-button>
                <el-button type="info">信息按钮</el-button>
                <el-button type="warning">警告按钮</el-button>
                <el-button type="danger">危险按钮</el-button>
              </div>
              
              <h3>输入框组件</h3>
              <div class="demo-block">
                <el-input v-model="demoInput" placeholder="请输入内容" style="width: 200px; margin-right: 10px;" />
                <el-input v-model="demoInput" placeholder="带图标" prefix-icon="Search" style="width: 200px;" />
              </div>
              
              <h3>选择器组件</h3>
              <div class="demo-block">
                <el-select v-model="demoSelect" placeholder="请选择" style="width: 200px; margin-right: 10px;">
                  <el-option label="选项1" value="1" />
                  <el-option label="选项2" value="2" />
                  <el-option label="选项3" value="3" />
                </el-select>
                <el-date-picker
                  v-model="demoDate"
                  type="date"
                  placeholder="选择日期"
                  style="width: 200px;"
                />
              </div>
            </div>
          </el-tab-pane>

          <!-- 表单组件 -->
          <el-tab-pane label="表单组件" name="form">
            <div class="component-section">
              <h3>表单示例</h3>
              <div class="demo-block">
                <el-form :model="demoForm" label-width="100px" style="max-width: 600px;">
                  <el-form-item label="用户名">
                    <el-input v-model="demoForm.username" />
                  </el-form-item>
                  <el-form-item label="密码">
                    <el-input v-model="demoForm.password" type="password" show-password />
                  </el-form-item>
                  <el-form-item label="性别">
                    <el-radio-group v-model="demoForm.gender">
                      <el-radio label="male">男</el-radio>
                      <el-radio label="female">女</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item label="爱好">
                    <el-checkbox-group v-model="demoForm.hobbies">
                      <el-checkbox label="reading">阅读</el-checkbox>
                      <el-checkbox label="music">音乐</el-checkbox>
                      <el-checkbox label="sports">运动</el-checkbox>
                    </el-checkbox-group>
                  </el-form-item>
                  <el-form-item label="备注">
                    <el-input v-model="demoForm.remark" type="textarea" :rows="3" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary">提交</el-button>
                    <el-button>重置</el-button>
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </el-tab-pane>

          <!-- 数据展示 -->
          <el-tab-pane label="数据展示" name="data">
            <div class="component-section">
              <h3>表格组件</h3>
              <div class="demo-block">
                <el-table :data="tableData" style="width: 100%">
                  <el-table-column prop="name" label="姓名" width="120" />
                  <el-table-column prop="age" label="年龄" width="80" />
                  <el-table-column prop="email" label="邮箱" />
                  <el-table-column prop="status" label="状态" width="100">
                    <template #default="{ row }">
                      <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
                        {{ row.status === 'active' ? '活跃' : '禁用' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="150">
                    <template #default>
                      <el-button size="small" type="primary">编辑</el-button>
                      <el-button size="small" type="danger">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              
              <h3>分页组件</h3>
              <div class="demo-block">
                <el-pagination
                  v-model:current-page="currentPage"
                  v-model:page-size="pageSize"
                  :page-sizes="[10, 20, 50, 100]"
                  :total="total"
                  layout="total, sizes, prev, pager, next, jumper"
                />
              </div>
            </div>
          </el-tab-pane>

          <!-- 反馈组件 -->
          <el-tab-pane label="反馈组件" name="feedback">
            <div class="component-section">
              <h3>消息提示</h3>
              <div class="demo-block">
                <el-button @click="showMessage('success')">成功消息</el-button>
                <el-button @click="showMessage('warning')">警告消息</el-button>
                <el-button @click="showMessage('error')">错误消息</el-button>
                <el-button @click="showMessage('info')">信息消息</el-button>
              </div>
              
              <h3>确认对话框</h3>
              <div class="demo-block">
                <el-button @click="showConfirm">确认对话框</el-button>
                <el-button @click="showAlert">警告对话框</el-button>
              </div>
              
              <h3>加载状态</h3>
              <div class="demo-block">
                <el-button @click="showLoading" :loading="loading">加载按钮</el-button>
                <div v-loading="tableLoading" style="height: 100px; border: 1px solid #eee; margin-top: 10px;">
                  <p style="text-align: center; line-height: 100px;">加载区域</p>
                </div>
                <el-button @click="toggleTableLoading" style="margin-top: 10px;">
                  {{ tableLoading ? '停止加载' : '开始加载' }}
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <!-- 导航组件 -->
          <el-tab-pane label="导航组件" name="navigation">
            <div class="component-section">
              <h3>面包屑导航</h3>
              <div class="demo-block">
                <el-breadcrumb separator="/">
                  <el-breadcrumb-item>首页</el-breadcrumb-item>
                  <el-breadcrumb-item>开发工具</el-breadcrumb-item>
                  <el-breadcrumb-item>组件展示</el-breadcrumb-item>
                </el-breadcrumb>
              </div>
              
              <h3>步骤条</h3>
              <div class="demo-block">
                <el-steps :active="stepActive" finish-status="success">
                  <el-step title="步骤1" description="这是步骤1的描述" />
                  <el-step title="步骤2" description="这是步骤2的描述" />
                  <el-step title="步骤3" description="这是步骤3的描述" />
                  <el-step title="步骤4" description="这是步骤4的描述" />
                </el-steps>
                <div style="margin-top: 20px;">
                  <el-button @click="prevStep" :disabled="stepActive <= 0">上一步</el-button>
                  <el-button @click="nextStep" :disabled="stepActive >= 3">下一步</el-button>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'

// 响应式数据
const activeTab = ref('basic')
const demoInput = ref('')
const demoSelect = ref('')
const demoDate = ref('')
const loading = ref(false)
const tableLoading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(100)
const stepActive = ref(0)

// 表单数据
const demoForm = reactive({
  username: '',
  password: '',
  gender: 'male',
  hobbies: [],
  remark: ''
})

// 表格数据
const tableData = ref([
  {
    name: '张三',
    age: 25,
    email: 'zhangsan@example.com',
    status: 'active'
  },
  {
    name: '李四',
    age: 30,
    email: 'lisi@example.com',
    status: 'inactive'
  },
  {
    name: '王五',
    age: 28,
    email: 'wangwu@example.com',
    status: 'active'
  },
  {
    name: '赵六',
    age: 32,
    email: 'zhaoliu@example.com',
    status: 'inactive'
  }
])

// 方法
const showMessage = (type: 'success' | 'warning' | 'error' | 'info') => {
  const messages = {
    success: '这是一条成功消息',
    warning: '这是一条警告消息',
    error: '这是一条错误消息',
    info: '这是一条信息消息'
  }
  ElMessage[type](messages[type])
}

const showConfirm = async () => {
  try {
    await ElMessageBox.confirm(
      '此操作将永久删除该文件, 是否继续?',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    ElMessage.success('删除成功!')
  } catch {
    ElMessage.info('已取消删除')
  }
}

const showAlert = () => {
  ElMessageBox.alert('这是一段内容', '标题', {
    confirmButtonText: '确定'
  })
}

const showLoading = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 2000)
}

const toggleTableLoading = () => {
  tableLoading.value = !tableLoading.value
  if (tableLoading.value) {
    setTimeout(() => {
      tableLoading.value = false
    }, 3000)
  }
}

const prevStep = () => {
  if (stepActive.value > 0) {
    stepActive.value--
  }
}

const nextStep = () => {
  if (stepActive.value < 3) {
    stepActive.value++
  }
}
</script>

<style scoped lang="scss">
.dev-components {
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

  .component-categories {
    margin-top: 20px;

    .component-section {
      h3 {
        margin: 20px 0 15px 0;
        color: #303133;
        font-size: 16px;
        font-weight: 600;
        border-bottom: 1px solid #ebeef5;
        padding-bottom: 8px;
      }

      .demo-block {
        margin-bottom: 30px;
        padding: 20px;
        border: 1px solid #ebeef5;
        border-radius: 4px;
        background-color: #fafafa;

        > * {
          margin-right: 10px;
          margin-bottom: 10px;
        }
      }
    }
  }
}

:deep(.el-tabs__content) {
  padding: 20px 0;
}

:deep(.el-form-item) {
  margin-bottom: 18px;
}

:deep(.el-checkbox-group) {
  .el-checkbox {
    margin-right: 15px;
  }
}

:deep(.el-radio-group) {
  .el-radio {
    margin-right: 15px;
  }
}
</style>