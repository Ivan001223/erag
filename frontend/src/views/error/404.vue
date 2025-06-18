<template>
  <div class="error-page">
    <div class="error-container">
      <div class="error-content">
        <!-- 错误图标 -->
        <div class="error-icon">
          <svg viewBox="0 0 1024 1024" width="200" height="200">
            <path
              d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"
              fill="#faad14"
            />
            <path
              d="M464 688a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm24-112h48c4.4 0 8-3.6 8-8V296c0-4.4-3.6-8-8-8h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8z"
              fill="#faad14"
            />
          </svg>
        </div>
        
        <!-- 错误信息 -->
        <div class="error-info">
          <h1 class="error-title">404</h1>
          <h2 class="error-subtitle">页面未找到</h2>
          <p class="error-description">
            抱歉，您访问的页面不存在。可能是页面地址错误，或者页面已被删除。
          </p>
        </div>
        
        <!-- 操作按钮 -->
        <div class="error-actions">
          <el-button type="primary" size="large" @click="goHome">
            <el-icon><House /></el-icon>
            返回首页
          </el-button>
          <el-button size="large" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回上页
          </el-button>
          <el-button size="large" @click="searchPage">
            <el-icon><Search /></el-icon>
            搜索页面
          </el-button>
        </div>
        
        <!-- 建议链接 -->
        <div class="error-suggestions">
          <h3>您可能想要访问：</h3>
          <div class="suggestion-links">
            <router-link to="/dashboard" class="suggestion-link">
              <el-icon><Odometer /></el-icon>
              <span>控制台</span>
            </router-link>
            <router-link to="/knowledge" class="suggestion-link">
              <el-icon><Document /></el-icon>
              <span>知识库</span>
            </router-link>
            <router-link to="/user" class="suggestion-link">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </router-link>
            <router-link to="/system" class="suggestion-link">
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </router-link>
          </div>
        </div>
        
        <!-- 搜索框 -->
        <div class="error-search">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索您要找的内容..."
            size="large"
            class="search-input"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button @click="handleSearch">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
      
      <!-- 装饰元素 -->
      <div class="error-decoration">
        <div class="decoration-shape shape-1"></div>
        <div class="decoration-shape shape-2"></div>
        <div class="decoration-shape shape-3"></div>
        <div class="decoration-shape shape-4"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  House,
  ArrowLeft,
  Search,
  Odometer,
  Document,
  User,
  Setting
} from '@element-plus/icons-vue'

const router = useRouter()
const searchKeyword = ref('')

// 返回首页
const goHome = () => {
  router.push('/')
}

// 返回上一页
const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}

// 搜索页面
const searchPage = () => {
  // 这里可以跳转到搜索页面或打开搜索对话框
  ElMessage.info('搜索功能开发中...')
}

// 处理搜索
const handleSearch = () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  // 这里可以实现搜索逻辑
  ElMessage.success(`正在搜索：${searchKeyword.value}`)
  
  // 模拟搜索结果
  setTimeout(() => {
    ElMessage.info('未找到相关内容，请尝试其他关键词')
  }, 1000)
}
</script>

<style scoped lang="scss">
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.error-container {
  max-width: 800px;
  width: 100%;
  position: relative;
  z-index: 2;
}

.error-content {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 60px 40px;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.error-icon {
  margin-bottom: 30px;
  
  svg {
    filter: drop-shadow(0 10px 20px rgba(250, 173, 20, 0.3));
    animation: bounce 2s ease-in-out infinite;
  }
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-10px);
  }
  60% {
    transform: translateY(-5px);
  }
}

.error-info {
  margin-bottom: 40px;
  
  .error-title {
    font-size: 72px;
    font-weight: 700;
    color: #faad14;
    margin: 0 0 10px 0;
    text-shadow: 0 4px 8px rgba(250, 173, 20, 0.3);
    animation: glow 2s ease-in-out infinite alternate;
  }
  
  .error-subtitle {
    font-size: 32px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 20px 0;
  }
  
  .error-description {
    font-size: 16px;
    color: #606266;
    line-height: 1.6;
    margin: 0;
    max-width: 500px;
    margin: 0 auto;
  }
}

@keyframes glow {
  from {
    text-shadow: 0 4px 8px rgba(250, 173, 20, 0.3);
  }
  to {
    text-shadow: 0 4px 8px rgba(250, 173, 20, 0.6), 0 0 20px rgba(250, 173, 20, 0.4);
  }
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-bottom: 40px;
  flex-wrap: wrap;
  
  .el-button {
    min-width: 140px;
    height: 44px;
    border-radius: 22px;
    font-weight: 500;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
    }
  }
}

.error-suggestions {
  margin-bottom: 40px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 20px 0;
  }
  
  .suggestion-links {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .suggestion-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 20px 15px;
    background: rgba(64, 158, 255, 0.1);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 12px;
    text-decoration: none;
    color: #409eff;
    transition: all 0.3s ease;
    
    &:hover {
      background: rgba(64, 158, 255, 0.2);
      border-color: #409eff;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
    }
    
    .el-icon {
      font-size: 24px;
    }
    
    span {
      font-size: 14px;
      font-weight: 500;
    }
  }
}

.error-search {
  max-width: 400px;
  margin: 0 auto;
  
  .search-input {
    :deep(.el-input__wrapper) {
      border-radius: 25px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    }
    
    :deep(.el-input-group__append) {
      border-radius: 0 25px 25px 0;
      
      .el-button {
        border-radius: 0 25px 25px 0;
      }
    }
  }
}

.error-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.decoration-shape {
  position: absolute;
  background: rgba(255, 255, 255, 0.1);
  animation: float-shape 8s ease-in-out infinite;
  
  &.shape-1 {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    top: 15%;
    left: 10%;
    animation-delay: 0s;
  }
  
  &.shape-2 {
    width: 120px;
    height: 120px;
    border-radius: 20px;
    top: 60%;
    right: 15%;
    animation-delay: 2s;
    transform: rotate(45deg);
  }
  
  &.shape-3 {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    bottom: 25%;
    left: 20%;
    animation-delay: 4s;
  }
  
  &.shape-4 {
    width: 100px;
    height: 100px;
    border-radius: 15px;
    top: 20%;
    right: 25%;
    animation-delay: 6s;
    transform: rotate(-30deg);
  }
}

@keyframes float-shape {
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
    opacity: 0.3;
  }
  25% {
    transform: translateY(-20px) rotate(90deg);
    opacity: 0.5;
  }
  50% {
    transform: translateY(-10px) rotate(180deg);
    opacity: 0.7;
  }
  75% {
    transform: translateY(-30px) rotate(270deg);
    opacity: 0.4;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .error-content {
    padding: 40px 20px;
  }
  
  .error-icon svg {
    width: 150px;
    height: 150px;
  }
  
  .error-info {
    .error-title {
      font-size: 48px;
    }
    
    .error-subtitle {
      font-size: 24px;
    }
    
    .error-description {
      font-size: 14px;
    }
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 100%;
      max-width: 280px;
    }
  }
  
  .suggestion-links {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .error-page {
    padding: 10px;
  }
  
  .error-content {
    padding: 30px 15px;
  }
  
  .error-icon svg {
    width: 120px;
    height: 120px;
  }
  
  .error-info {
    .error-title {
      font-size: 36px;
    }
    
    .error-subtitle {
      font-size: 20px;
    }
  }
  
  .suggestion-links {
    grid-template-columns: 1fr;
  }
}
</style>