<template>
  <div class="system-settings">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <h2>系统设置</h2>
          <p>管理系统配置和参数</p>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="settings-tabs">
        <!-- 基础设置 -->
        <el-tab-pane label="基础设置" name="basic">
          <el-form :model="basicSettings" label-width="120px" class="settings-form">
            <el-form-item label="系统名称">
              <el-input v-model="basicSettings.systemName" placeholder="请输入系统名称" />
            </el-form-item>
            <el-form-item label="系统描述">
              <el-input
                v-model="basicSettings.systemDescription"
                type="textarea"
                :rows="3"
                placeholder="请输入系统描述"
              />
            </el-form-item>
            <el-form-item label="系统版本">
              <el-input v-model="basicSettings.systemVersion" placeholder="请输入系统版本" />
            </el-form-item>
            <el-form-item label="维护模式">
              <el-switch v-model="basicSettings.maintenanceMode" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 安全设置 -->
        <el-tab-pane label="安全设置" name="security">
          <el-form :model="securitySettings" label-width="120px" class="settings-form">
            <el-form-item label="密码策略">
              <el-checkbox-group v-model="securitySettings.passwordPolicy">
                <el-checkbox label="requireUppercase">要求大写字母</el-checkbox>
                <el-checkbox label="requireLowercase">要求小写字母</el-checkbox>
                <el-checkbox label="requireNumbers">要求数字</el-checkbox>
                <el-checkbox label="requireSpecialChars">要求特殊字符</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="最小密码长度">
              <el-input-number v-model="securitySettings.minPasswordLength" :min="6" :max="20" />
            </el-form-item>
            <el-form-item label="会话超时(分钟)">
              <el-input-number v-model="securitySettings.sessionTimeout" :min="5" :max="1440" />
            </el-form-item>
            <el-form-item label="启用双因子认证">
              <el-switch v-model="securitySettings.enableTwoFactor" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 邮件设置 -->
        <el-tab-pane label="邮件设置" name="email">
          <el-form :model="emailSettings" label-width="120px" class="settings-form">
            <el-form-item label="SMTP服务器">
              <el-input v-model="emailSettings.smtpHost" placeholder="请输入SMTP服务器地址" />
            </el-form-item>
            <el-form-item label="SMTP端口">
              <el-input-number v-model="emailSettings.smtpPort" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="emailSettings.smtpUsername" placeholder="请输入SMTP用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="emailSettings.smtpPassword" type="password" placeholder="请输入SMTP密码" />
            </el-form-item>
            <el-form-item label="启用SSL">
              <el-switch v-model="emailSettings.enableSSL" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 存储设置 -->
        <el-tab-pane label="存储设置" name="storage">
          <el-form :model="storageSettings" label-width="120px" class="settings-form">
            <el-form-item label="文件存储路径">
              <el-input v-model="storageSettings.filePath" placeholder="请输入文件存储路径" />
            </el-form-item>
            <el-form-item label="最大文件大小(MB)">
              <el-input-number v-model="storageSettings.maxFileSize" :min="1" :max="1024" />
            </el-form-item>
            <el-form-item label="允许的文件类型">
              <el-input v-model="storageSettings.allowedFileTypes" placeholder="如: .pdf,.doc,.txt" />
            </el-form-item>
            <el-form-item label="启用文件压缩">
              <el-switch v-model="storageSettings.enableCompression" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="form-actions">
        <el-button type="primary" @click="saveSettings" :loading="saving">
          保存设置
        </el-button>
        <el-button @click="resetSettings">重置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

// 响应式数据
const activeTab = ref('basic')
const saving = ref(false)

// 基础设置
const basicSettings = reactive({
  systemName: 'ERAG 企业级RAG知识库',
  systemDescription: '基于大语言模型的企业级知识管理系统',
  systemVersion: '1.0.0',
  maintenanceMode: false
})

// 安全设置
const securitySettings = reactive({
  passwordPolicy: ['requireUppercase', 'requireLowercase', 'requireNumbers'],
  minPasswordLength: 8,
  sessionTimeout: 30,
  enableTwoFactor: false
})

// 邮件设置
const emailSettings = reactive({
  smtpHost: '',
  smtpPort: 587,
  smtpUsername: '',
  smtpPassword: '',
  enableSSL: true
})

// 存储设置
const storageSettings = reactive({
  filePath: '/data/uploads',
  maxFileSize: 100,
  allowedFileTypes: '.pdf,.doc,.docx,.txt,.md',
  enableCompression: true
})

// 方法
const saveSettings = async () => {
  saving.value = true
  try {
    // 这里应该调用API保存设置
    await new Promise(resolve => setTimeout(resolve, 1000)) // 模拟API调用
    ElMessage.success('设置保存成功')
  } catch (error) {
    ElMessage.error('设置保存失败')
  } finally {
    saving.value = false
  }
}

const resetSettings = () => {
  // 重置为默认值
  ElMessage.info('设置已重置')
}

const loadSettings = async () => {
  try {
    // 这里应该调用API加载设置
    console.log('加载系统设置')
  } catch (error) {
    ElMessage.error('加载设置失败')
  }
}

// 生命周期
onMounted(() => {
  loadSettings()
})
</script>

<style scoped lang="scss">
.system-settings {
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

  .settings-tabs {
    margin-top: 20px;

    .settings-form {
      max-width: 600px;
      margin-top: 20px;
    }
  }

  .form-actions {
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
    text-align: right;

    .el-button {
      margin-left: 10px;
    }
  }
}

:deep(.el-tabs__content) {
  padding-top: 0;
}

:deep(.el-form-item) {
  margin-bottom: 20px;
}

:deep(.el-checkbox-group) {
  .el-checkbox {
    display: block;
    margin-bottom: 8px;
    margin-right: 0;
  }
}
</style>