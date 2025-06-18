<template>
  <div class="error-page">
    <div class="error-content">
      <!-- 错误图标和数字 -->
      <div class="error-visual">
        <div class="error-number">404</div>
        <div class="error-icon">
          <el-icon><DocumentDelete /></el-icon>
        </div>
      </div>
      
      <!-- 错误信息 -->
      <div class="error-info">
        <h1>页面未找到</h1>
        <p class="error-description">
          抱歉，您访问的页面不存在或已被移除。
        </p>
        <p class="error-suggestion">
          请检查网址是否正确，或者尝试以下操作：
        </p>
        
        <!-- 建议操作 -->
        <div class="suggestions">
          <ul>
            <li>检查网址拼写是否正确</li>
            <li>返回上一页重新尝试</li>
            <li>访问首页查找您需要的内容</li>
            <li>使用搜索功能查找相关信息</li>
          </ul>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="error-actions">
        <el-button type="primary" size="large" @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
        
        <el-button size="large" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回上页
        </el-button>
        
        <el-button size="large" @click="refresh">
          <el-icon><Refresh /></el-icon>
          刷新页面
        </el-button>
      </div>
      
      <!-- 搜索框 -->
      <div class="search-section">
        <div class="search-title">或者搜索您需要的内容：</div>
        <div class="search-box">
          <el-input
            v-model="searchKeyword"
            placeholder="输入关键词搜索..."
            size="large"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button @click="handleSearch" :disabled="!searchKeyword.trim()">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
      
      <!-- 快速链接 -->
      <div class="quick-links">
        <div class="links-title">快速访问：</div>
        <div class="links-grid">
          <router-link to="/dashboard" class="quick-link">
            <el-icon><DataBoard /></el-icon>
            <span>仪表盘</span>
          </router-link>
          
          <router-link to="/knowledge/graphs" class="quick-link">
            <el-icon><Share /></el-icon>
            <span>知识图谱</span>
          </router-link>
          
          <router-link to="/knowledge/entities" class="quick-link">
            <el-icon><Collection /></el-icon>
            <span>实体管理</span>
          </router-link>
          
          <router-link to="/knowledge/relations" class="quick-link">
            <el-icon><Connection /></el-icon>
            <span>关系管理</span>
          </router-link>
        </div>
      </div>
    </div>
    
    <!-- 装饰元素 -->
    <div class="decoration">
      <div class="floating-shape shape-1"></div>
      <div class="floating-shape shape-2"></div>
      <div class="floating-shape shape-3"></div>
      <div class="floating-shape shape-4"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DocumentDelete,
  HomeFilled,
  ArrowLeft,
  Refresh,
  Search,
  DataBoard,
  Share,
  Collection,
  Connection
} from '@element-plus/icons-vue'

const router = useRouter()

// 搜索关键词
const searchKeyword = ref('')

// 返回首页
const goHome = () => {
  router.push('/dashboard')
}

// 返回上一页
const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    goHome()
  }
}

// 刷新页面
const refresh = () => {
  window.location.reload()
}

// 处理搜索
const handleSearch = () => {
  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  // 这里应该跳转到搜索页面或执行搜索逻辑
  // 暂时跳转到仪表盘并显示搜索提示
  ElMessage.info(`搜索功能开发中，关键词：${keyword}`)
  router.push('/dashboard')
}
</script>

<style lang="scss" scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.error-content {
  max-width: 600px;
  width: 100%;
  text-align: center;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 48px 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 1;
}

.error-visual {
  position: relative;
  margin-bottom: 32px;
  
  .error-number {
    font-size: 120px;
    font-weight: 900;
    color: #667eea;
    line-height: 1;
    margin-bottom: 16px;
    text-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
    
    @media (max-width: 480px) {
      font-size: 80px;
    }
  }
  
  .error-icon {
    .el-icon {
      font-size: 64px;
      color: #f56565;
      
      @media (max-width: 480px) {
        font-size: 48px;
      }
    }
  }
}

.error-info {
  margin-bottom: 32px;
  
  h1 {
    font-size: 32px;
    font-weight: 700;
    color: #2d3748;
    margin: 0 0 16px 0;
    
    @media (max-width: 480px) {
      font-size: 24px;
    }
  }
  
  .error-description {
    font-size: 18px;
    color: #4a5568;
    margin: 0 0 16px 0;
    line-height: 1.6;
    
    @media (max-width: 480px) {
      font-size: 16px;
    }
  }
  
  .error-suggestion {
    font-size: 16px;
    color: #718096;
    margin: 0 0 16px 0;
    
    @media (max-width: 480px) {
      font-size: 14px;
    }
  }
}

.suggestions {
  text-align: left;
  max-width: 400px;
  margin: 0 auto 24px;
  
  ul {
    margin: 0;
    padding-left: 20px;
    
    li {
      color: #718096;
      font-size: 14px;
      line-height: 1.8;
      margin-bottom: 4px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 32px;
  
  .el-button {
    min-width: 120px;
    
    @media (max-width: 480px) {
      min-width: 100px;
      flex: 1;
    }
  }
}

.search-section {
  margin-bottom: 32px;
  
  .search-title {
    font-size: 16px;
    color: #4a5568;
    margin-bottom: 12px;
  }
  
  .search-box {
    max-width: 400px;
    margin: 0 auto;
  }
}

.quick-links {
  .links-title {
    font-size: 16px;
    color: #4a5568;
    margin-bottom: 16px;
  }
  
  .links-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
    max-width: 400px;
    margin: 0 auto;
    
    @media (max-width: 480px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  .quick-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px 12px;
    background: #f7fafc;
    border-radius: 12px;
    text-decoration: none;
    color: #4a5568;
    transition: all 0.3s ease;
    border: 2px solid transparent;
    
    &:hover {
      background: #667eea;
      color: white;
      transform: translateY(-2px);
      box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
    }
    
    .el-icon {
      font-size: 24px;
    }
    
    span {
      font-size: 12px;
      font-weight: 500;
    }
  }
}

.decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
}

.floating-shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float 6s ease-in-out infinite;
  
  &.shape-1 {
    width: 80px;
    height: 80px;
    top: 10%;
    left: 10%;
    animation-delay: 0s;
  }
  
  &.shape-2 {
    width: 120px;
    height: 120px;
    top: 20%;
    right: 15%;
    animation-delay: 2s;
  }
  
  &.shape-3 {
    width: 60px;
    height: 60px;
    bottom: 20%;
    left: 20%;
    animation-delay: 4s;
  }
  
  &.shape-4 {
    width: 100px;
    height: 100px;
    bottom: 10%;
    right: 10%;
    animation-delay: 1s;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .error-content {
    padding: 32px 24px;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 100%;
      max-width: 200px;
    }
  }
}

@media (max-width: 480px) {
  .error-page {
    padding: 16px;
  }
  
  .error-content {
    padding: 24px 16px;
  }
  
  .suggestions {
    text-align: center;
    
    ul {
      text-align: left;
      padding-left: 16px;
    }
  }
}
</style>