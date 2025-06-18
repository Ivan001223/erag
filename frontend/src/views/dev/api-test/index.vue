<template>
  <div class="dev-api-test">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <h2>API 测试工具</h2>
          <p>开发环境下的 API 接口测试和调试工具</p>
        </div>
      </template>

      <!-- 请求配置 -->
      <div class="request-config">
        <el-card class="config-card">
          <template #header>
            <span>请求配置</span>
          </template>
          
          <el-form :model="requestConfig" label-width="100px">
            <el-form-item label="请求方法">
              <el-select v-model="requestConfig.method" style="width: 150px;">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
                <el-option label="PATCH" value="PATCH" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="请求URL">
              <el-input
                v-model="requestConfig.url"
                placeholder="请输入完整的API地址"
                style="width: 100%;"
              >
                <template #prepend>
                  <el-select v-model="requestConfig.baseUrl" style="width: 200px;">
                    <el-option label="本地开发" value="http://localhost:8000" />
                    <el-option label="测试环境" value="https://test-api.example.com" />
                    <el-option label="生产环境" value="https://api.example.com" />
                    <el-option label="自定义" value="custom" />
                  </el-select>
                </template>
              </el-input>
            </el-form-item>
            
            <el-form-item v-if="requestConfig.baseUrl === 'custom'" label="自定义域名">
              <el-input v-model="requestConfig.customBaseUrl" placeholder="https://your-api.com" />
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 请求参数配置 -->
      <div class="params-config">
        <el-row :gutter="20">
          <!-- Headers -->
          <el-col :span="12">
            <el-card class="params-card">
              <template #header>
                <div class="params-header">
                  <span>请求头 (Headers)</span>
                  <el-button size="small" type="primary" @click="addHeader">
                    <el-icon><Plus /></el-icon>
                    添加
                  </el-button>
                </div>
              </template>
              
              <div class="params-list">
                <div v-for="(header, index) in requestConfig.headers" :key="index" class="param-item">
                  <el-input
                    v-model="header.key"
                    placeholder="Header名称"
                    style="width: 40%; margin-right: 10px;"
                  />
                  <el-input
                    v-model="header.value"
                    placeholder="Header值"
                    style="width: 40%; margin-right: 10px;"
                  />
                  <el-button size="small" type="danger" @click="removeHeader(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                
                <div v-if="requestConfig.headers.length === 0" class="empty-params">
                  <el-empty description="暂无请求头" :image-size="60" />
                </div>
              </div>
            </el-card>
          </el-col>
          
          <!-- Query Parameters -->
          <el-col :span="12">
            <el-card class="params-card">
              <template #header>
                <div class="params-header">
                  <span>查询参数 (Query)</span>
                  <el-button size="small" type="primary" @click="addQueryParam">
                    <el-icon><Plus /></el-icon>
                    添加
                  </el-button>
                </div>
              </template>
              
              <div class="params-list">
                <div v-for="(param, index) in requestConfig.queryParams" :key="index" class="param-item">
                  <el-input
                    v-model="param.key"
                    placeholder="参数名"
                    style="width: 40%; margin-right: 10px;"
                  />
                  <el-input
                    v-model="param.value"
                    placeholder="参数值"
                    style="width: 40%; margin-right: 10px;"
                  />
                  <el-button size="small" type="danger" @click="removeQueryParam(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                
                <div v-if="requestConfig.queryParams.length === 0" class="empty-params">
                  <el-empty description="暂无查询参数" :image-size="60" />
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 请求体 -->
      <div v-if="['POST', 'PUT', 'PATCH'].includes(requestConfig.method)" class="body-config">
        <el-card class="body-card">
          <template #header>
            <div class="body-header">
              <span>请求体 (Body)</span>
              <el-radio-group v-model="requestConfig.bodyType" size="small">
                <el-radio-button label="json">JSON</el-radio-button>
                <el-radio-button label="form">Form Data</el-radio-button>
                <el-radio-button label="raw">Raw</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          
          <!-- JSON Body -->
          <div v-if="requestConfig.bodyType === 'json'" class="json-body">
            <el-input
              v-model="requestConfig.jsonBody"
              type="textarea"
              :rows="8"
              placeholder="请输入JSON格式的请求体"
            />
            <div class="json-actions">
              <el-button size="small" @click="formatJson">格式化JSON</el-button>
              <el-button size="small" @click="validateJson">验证JSON</el-button>
            </div>
          </div>
          
          <!-- Form Data -->
          <div v-if="requestConfig.bodyType === 'form'" class="form-body">
            <div class="form-params">
              <div v-for="(param, index) in requestConfig.formData" :key="index" class="param-item">
                <el-input
                  v-model="param.key"
                  placeholder="字段名"
                  style="width: 30%; margin-right: 10px;"
                />
                <el-input
                  v-model="param.value"
                  placeholder="字段值"
                  style="width: 50%; margin-right: 10px;"
                />
                <el-button size="small" type="danger" @click="removeFormData(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-button size="small" type="primary" @click="addFormData">
              <el-icon><Plus /></el-icon>
              添加字段
            </el-button>
          </div>
          
          <!-- Raw Body -->
          <div v-if="requestConfig.bodyType === 'raw'" class="raw-body">
            <el-input
              v-model="requestConfig.rawBody"
              type="textarea"
              :rows="8"
              placeholder="请输入原始请求体内容"
            />
          </div>
        </el-card>
      </div>

      <!-- 发送请求按钮 -->
      <div class="send-request">
        <el-button
          type="primary"
          size="large"
          @click="sendRequest"
          :loading="loading"
          :disabled="!requestConfig.url"
        >
          <el-icon><Position /></el-icon>
          发送请求
        </el-button>
        <el-button size="large" @click="clearResponse">
          <el-icon><Delete /></el-icon>
          清空响应
        </el-button>
        <el-button size="large" @click="saveRequest">
          <el-icon><DocumentCopy /></el-icon>
          保存请求
        </el-button>
      </div>

      <!-- 响应结果 -->
      <div v-if="response" class="response-section">
        <el-card class="response-card">
          <template #header>
            <div class="response-header">
              <span>响应结果</span>
              <div class="response-info">
                <el-tag :type="getStatusType(response.status)" size="small">
                  {{ response.status }} {{ response.statusText }}
                </el-tag>
                <span class="response-time">{{ response.time }}ms</span>
              </div>
            </div>
          </template>
          
          <el-tabs v-model="responseTab" type="border-card">
            <!-- 响应体 -->
            <el-tab-pane label="响应体" name="body">
              <div class="response-body">
                <div class="response-actions">
                  <el-button size="small" @click="formatResponseJson">格式化JSON</el-button>
                  <el-button size="small" @click="copyResponse">复制响应</el-button>
                </div>
                <pre class="response-content">{{ formattedResponse }}</pre>
              </div>
            </el-tab-pane>
            
            <!-- 响应头 -->
            <el-tab-pane label="响应头" name="headers">
              <div class="response-headers">
                <el-table :data="responseHeaders" stripe>
                  <el-table-column prop="key" label="Header名称" width="200" />
                  <el-table-column prop="value" label="Header值" />
                </el-table>
              </div>
            </el-tab-pane>
            
            <!-- 请求详情 -->
            <el-tab-pane label="请求详情" name="request">
              <div class="request-details">
                <h4>请求URL</h4>
                <pre>{{ fullRequestUrl }}</pre>
                
                <h4>请求方法</h4>
                <pre>{{ requestConfig.method }}</pre>
                
                <h4>请求头</h4>
                <pre>{{ JSON.stringify(getRequestHeaders(), null, 2) }}</pre>
                
                <h4 v-if="['POST', 'PUT', 'PATCH'].includes(requestConfig.method)">请求体</h4>
                <pre v-if="['POST', 'PUT', 'PATCH'].includes(requestConfig.method)">{{ getRequestBody() }}</pre>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>

      <!-- 保存的请求 -->
      <div class="saved-requests">
        <el-card class="saved-card">
          <template #header>
            <div class="saved-header">
              <span>保存的请求</span>
              <el-button size="small" type="danger" @click="clearSavedRequests">
                <el-icon><Delete /></el-icon>
                清空全部
              </el-button>
            </div>
          </template>
          
          <div class="saved-list">
            <div v-for="(saved, index) in savedRequests" :key="index" class="saved-item">
              <div class="saved-info">
                <el-tag :type="getMethodType(saved.method)" size="small">{{ saved.method }}</el-tag>
                <span class="saved-url">{{ saved.name || saved.url }}</span>
                <span class="saved-time">{{ saved.time }}</span>
              </div>
              <div class="saved-actions">
                <el-button size="small" type="primary" @click="loadRequest(saved)">
                  加载
                </el-button>
                <el-button size="small" type="danger" @click="removeSavedRequest(index)">
                  删除
                </el-button>
              </div>
            </div>
            
            <div v-if="savedRequests.length === 0" class="empty-saved">
              <el-empty description="暂无保存的请求" :image-size="60" />
            </div>
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Delete,
  Position,
  DocumentCopy
} from '@element-plus/icons-vue'
import axios from 'axios'
import dayjs from 'dayjs'

// 接口定义
interface KeyValue {
  key: string
  value: string
}

interface SavedRequest {
  name?: string
  method: string
  url: string
  baseUrl: string
  headers: KeyValue[]
  queryParams: KeyValue[]
  bodyType: string
  jsonBody: string
  formData: KeyValue[]
  rawBody: string
  time: string
}

interface ApiResponse {
  status: number
  statusText: string
  data: any
  headers: Record<string, string>
  time: number
}

// 响应式数据
const loading = ref(false)
const responseTab = ref('body')
const response = ref<ApiResponse | null>(null)
const savedRequests = ref<SavedRequest[]>([])

// 请求配置
const requestConfig = reactive({
  method: 'GET',
  baseUrl: 'http://localhost:8000',
  customBaseUrl: '',
  url: '/api/users',
  headers: [
    { key: 'Content-Type', value: 'application/json' },
    { key: 'Authorization', value: 'Bearer your-token' }
  ] as KeyValue[],
  queryParams: [] as KeyValue[],
  bodyType: 'json',
  jsonBody: '{\n  "name": "测试用户",\n  "email": "test@example.com"\n}',
  formData: [] as KeyValue[],
  rawBody: ''
})

// 计算属性
const fullRequestUrl = computed(() => {
  const baseUrl = requestConfig.baseUrl === 'custom' ? requestConfig.customBaseUrl : requestConfig.baseUrl
  const url = requestConfig.url.startsWith('/') ? requestConfig.url : '/' + requestConfig.url
  const queryString = requestConfig.queryParams
    .filter(p => p.key && p.value)
    .map(p => `${encodeURIComponent(p.key)}=${encodeURIComponent(p.value)}`)
    .join('&')
  
  return baseUrl + url + (queryString ? '?' + queryString : '')
})

const formattedResponse = computed(() => {
  if (!response.value) return ''
  
  try {
    if (typeof response.value.data === 'object') {
      return JSON.stringify(response.value.data, null, 2)
    }
    return response.value.data
  } catch {
    return response.value.data
  }
})

const responseHeaders = computed(() => {
  if (!response.value) return []
  
  return Object.entries(response.value.headers).map(([key, value]) => ({
    key,
    value
  }))
})

// 方法
const addHeader = () => {
  requestConfig.headers.push({ key: '', value: '' })
}

const removeHeader = (index: number) => {
  requestConfig.headers.splice(index, 1)
}

const addQueryParam = () => {
  requestConfig.queryParams.push({ key: '', value: '' })
}

const removeQueryParam = (index: number) => {
  requestConfig.queryParams.splice(index, 1)
}

const addFormData = () => {
  requestConfig.formData.push({ key: '', value: '' })
}

const removeFormData = (index: number) => {
  requestConfig.formData.splice(index, 1)
}

const formatJson = () => {
  try {
    const parsed = JSON.parse(requestConfig.jsonBody)
    requestConfig.jsonBody = JSON.stringify(parsed, null, 2)
    ElMessage.success('JSON格式化成功')
  } catch (error) {
    ElMessage.error('JSON格式错误')
  }
}

const validateJson = () => {
  try {
    JSON.parse(requestConfig.jsonBody)
    ElMessage.success('JSON格式正确')
  } catch (error) {
    ElMessage.error('JSON格式错误')
  }
}

const getRequestHeaders = () => {
  const headers: Record<string, string> = {}
  requestConfig.headers
    .filter(h => h.key && h.value)
    .forEach(h => {
      headers[h.key] = h.value
    })
  return headers
}

const getRequestBody = () => {
  if (requestConfig.bodyType === 'json') {
    return requestConfig.jsonBody
  } else if (requestConfig.bodyType === 'form') {
    const formData = new FormData()
    requestConfig.formData
      .filter(f => f.key && f.value)
      .forEach(f => {
        formData.append(f.key, f.value)
      })
    return formData
  } else {
    return requestConfig.rawBody
  }
}

const sendRequest = async () => {
  loading.value = true
  const startTime = Date.now()
  
  try {
    const config: any = {
      method: requestConfig.method,
      url: fullRequestUrl.value,
      headers: getRequestHeaders()
    }
    
    // 添加请求体
    if (['POST', 'PUT', 'PATCH'].includes(requestConfig.method)) {
      if (requestConfig.bodyType === 'json') {
        config.data = JSON.parse(requestConfig.jsonBody)
      } else if (requestConfig.bodyType === 'form') {
        const formData = new FormData()
        requestConfig.formData
          .filter(f => f.key && f.value)
          .forEach(f => {
            formData.append(f.key, f.value)
          })
        config.data = formData
      } else {
        config.data = requestConfig.rawBody
      }
    }
    
    const result = await axios(config)
    const endTime = Date.now()
    
    response.value = {
      status: result.status,
      statusText: result.statusText,
      data: result.data,
      headers: result.headers as Record<string, string>,
      time: endTime - startTime
    }
    
    ElMessage.success('请求发送成功')
  } catch (error: any) {
    const endTime = Date.now()
    
    response.value = {
      status: error.response?.status || 0,
      statusText: error.response?.statusText || 'Network Error',
      data: error.response?.data || error.message,
      headers: error.response?.headers || {},
      time: endTime - startTime
    }
    
    ElMessage.error('请求发送失败')
  } finally {
    loading.value = false
  }
}

const clearResponse = () => {
  response.value = null
  ElMessage.info('响应已清空')
}

const saveRequest = async () => {
  try {
    const { value: name } = await ElMessageBox.prompt(
      '请输入请求名称',
      '保存请求',
      {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputPlaceholder: '请求名称（可选）'
      }
    )
    
    const savedRequest: SavedRequest = {
      name: name || undefined,
      method: requestConfig.method,
      url: requestConfig.url,
      baseUrl: requestConfig.baseUrl,
      headers: [...requestConfig.headers],
      queryParams: [...requestConfig.queryParams],
      bodyType: requestConfig.bodyType,
      jsonBody: requestConfig.jsonBody,
      formData: [...requestConfig.formData],
      rawBody: requestConfig.rawBody,
      time: dayjs().format('YYYY-MM-DD HH:mm:ss')
    }
    
    savedRequests.value.unshift(savedRequest)
    ElMessage.success('请求已保存')
  } catch {
    // 用户取消
  }
}

const loadRequest = (saved: SavedRequest) => {
  Object.assign(requestConfig, {
    method: saved.method,
    url: saved.url,
    baseUrl: saved.baseUrl,
    headers: [...saved.headers],
    queryParams: [...saved.queryParams],
    bodyType: saved.bodyType,
    jsonBody: saved.jsonBody,
    formData: [...saved.formData],
    rawBody: saved.rawBody
  })
  
  ElMessage.success('请求已加载')
}

const removeSavedRequest = (index: number) => {
  savedRequests.value.splice(index, 1)
  ElMessage.success('请求已删除')
}

const clearSavedRequests = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有保存的请求吗？',
      '确认清空',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    savedRequests.value = []
    ElMessage.success('已清空所有保存的请求')
  } catch {
    // 用户取消
  }
}

const formatResponseJson = () => {
  if (response.value && typeof response.value.data === 'object') {
    ElMessage.success('响应已格式化')
  } else {
    ElMessage.warning('响应不是JSON格式')
  }
}

const copyResponse = async () => {
  if (!response.value) return
  
  try {
    await navigator.clipboard.writeText(formattedResponse.value)
    ElMessage.success('响应已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

const getStatusType = (status: number) => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  if (status >= 400) return 'danger'
  return 'info'
}

const getMethodType = (method: string) => {
  const types: Record<string, string> = {
    GET: 'primary',
    POST: 'success',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return types[method] || 'info'
}
</script>

<style scoped lang="scss">
.dev-api-test {
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

  .request-config,
  .params-config,
  .body-config,
  .response-section,
  .saved-requests {
    margin: 20px 0;
  }

  .params-header,
  .body-header,
  .response-header,
  .saved-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .params-list {
    .param-item {
      display: flex;
      align-items: center;
      margin-bottom: 10px;
    }

    .empty-params {
      text-align: center;
      padding: 20px 0;
    }
  }

  .json-actions {
    margin-top: 10px;
    text-align: right;
  }

  .form-params {
    margin-bottom: 15px;
  }

  .send-request {
    text-align: center;
    margin: 30px 0;

    .el-button {
      margin: 0 10px;
    }
  }

  .response-body {
    .response-actions {
      margin-bottom: 15px;
      text-align: right;
    }

    .response-content {
      background-color: #f5f7fa;
      padding: 15px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      line-height: 1.5;
      max-height: 400px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }

  .request-details {
    h4 {
      margin: 20px 0 10px 0;
      color: #303133;
      font-size: 14px;
      font-weight: 600;
    }

    pre {
      background-color: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }

  .response-info {
    display: flex;
    align-items: center;
    gap: 10px;

    .response-time {
      font-size: 12px;
      color: #909399;
    }
  }

  .saved-list {
    .saved-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 15px;
      border: 1px solid #ebeef5;
      border-radius: 4px;
      margin-bottom: 10px;

      .saved-info {
        display: flex;
        align-items: center;
        gap: 10px;
        flex: 1;

        .saved-url {
          font-family: 'Courier New', monospace;
          font-size: 12px;
          color: #606266;
          flex: 1;
        }

        .saved-time {
          font-size: 12px;
          color: #909399;
        }
      }

      .saved-actions {
        display: flex;
        gap: 5px;
      }
    }

    .empty-saved {
      text-align: center;
      padding: 40px 0;
    }
  }
}

:deep(.el-form-item) {
  margin-bottom: 18px;
}

:deep(.el-input-group__prepend) {
  background-color: #f5f7fa;
}
</style>