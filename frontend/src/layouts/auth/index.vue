<template>
  <div class="auth-layout">
    <!-- 背景装饰 -->
    <div class="auth-background">
      <div class="bg-pattern"></div>
      <div class="bg-gradient"></div>
    </div>
    
    <!-- 主要内容 -->
    <div class="auth-container">
      <!-- 左侧信息区域 -->
      <div class="auth-info">
        <div class="info-content">
          <div class="logo">
            <img src="/logo.svg" alt="ERAG" class="logo-image" />
            <h1 class="logo-text">企业知识图谱系统</h1>
          </div>
          
          <div class="description">
            <h2>智能知识管理平台</h2>
            <p>基于AI的企业级知识图谱构建与管理系统，助力企业数字化转型</p>
          </div>
          
          <div class="features">
            <div class="feature-item">
              <el-icon class="feature-icon"><Document /></el-icon>
              <span>智能文档解析</span>
            </div>
            <div class="feature-item">
              <el-icon class="feature-icon"><Share /></el-icon>
              <span>知识图谱构建</span>
            </div>
            <div class="feature-item">
              <el-icon class="feature-icon"><Search /></el-icon>
              <span>智能检索问答</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 右侧表单区域 -->
      <div class="auth-form">
        <div class="form-container">
          <router-view />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Document, Share, Search } from '@element-plus/icons-vue'
</script>

<style lang="scss" scoped>
.auth-layout {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.auth-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  
  .bg-pattern {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: 
      radial-gradient(circle at 25% 25%, rgba(79, 172, 254, 0.1) 0%, transparent 50%),
      radial-gradient(circle at 75% 75%, rgba(129, 140, 248, 0.1) 0%, transparent 50%);
  }
  
  .bg-gradient {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, 
      rgba(79, 172, 254, 0.05) 0%, 
      rgba(129, 140, 248, 0.05) 100%);
  }
}

.auth-container {
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.auth-info {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: linear-gradient(135deg, 
    rgba(79, 172, 254, 0.8) 0%, 
    rgba(129, 140, 248, 0.8) 100%);
  color: white;
  
  .info-content {
    max-width: 500px;
    text-align: center;
  }
  
  .logo {
    margin-bottom: 40px;
    
    .logo-image {
      width: 80px;
      height: 80px;
      margin-bottom: 16px;
    }
    
    .logo-text {
      font-size: 32px;
      font-weight: 600;
      margin: 0;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
  }
  
  .description {
    margin-bottom: 40px;
    
    h2 {
      font-size: 24px;
      font-weight: 500;
      margin: 0 0 16px 0;
    }
    
    p {
      font-size: 16px;
      line-height: 1.6;
      margin: 0;
      opacity: 0.9;
    }
  }
  
  .features {
    display: flex;
    flex-direction: column;
    gap: 20px;
    
    .feature-item {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 16px;
      
      .feature-icon {
        font-size: 20px;
        opacity: 0.9;
      }
    }
  }
}

.auth-form {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: var(--el-bg-color);
  
  .form-container {
    width: 100%;
    max-width: 400px;
  }
}

// 响应式设计
@media (max-width: 1024px) {
  .auth-container {
    flex-direction: column;
  }
  
  .auth-info {
    flex: none;
    height: 40%;
    padding: 40px 20px;
    
    .info-content {
      max-width: none;
    }
    
    .features {
      flex-direction: row;
      justify-content: center;
      gap: 30px;
      
      .feature-item {
        flex-direction: column;
        gap: 8px;
        font-size: 14px;
        text-align: center;
      }
    }
  }
  
  .auth-form {
    flex: 1;
    padding: 40px 20px;
  }
}

@media (max-width: 768px) {
  .auth-info {
    .logo {
      .logo-image {
        width: 60px;
        height: 60px;
      }
      
      .logo-text {
        font-size: 24px;
      }
    }
    
    .description {
      h2 {
        font-size: 20px;
      }
      
      p {
        font-size: 14px;
      }
    }
  }
}
</style>