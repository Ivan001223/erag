<template>
  <div class="error-page">
    <div class="error-container">
      <div class="error-content">
        <!-- 错误图标 -->
        <div class="error-icon">
          <svg viewBox="0 0 1024 1024" width="200" height="200">
            <path
              d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"
              fill="#ff4d4f"
            />
            <path
              d="M464 688a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm24-112h48c4.4 0 8-3.6 8-8V296c0-4.4-3.6-8-8-8h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8z"
              fill="#ff4d4f"
            />
          </svg>
        </div>
        
        <!-- 错误信息 -->
        <div class="error-info">
          <h1 class="error-title">403</h1>
          <h2 class="error-subtitle">访问被拒绝</h2>
          <p class="error-description">
            抱歉，您没有权限访问此页面。请联系管理员获取相应权限，或返回首页继续浏览。
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
          <el-button size="large" @click="contactAdmin">
            <el-icon><Service /></el-icon>
            联系管理员
          </el-button>
        </div>
        
        <!-- 建议操作 -->
        <div class="error-suggestions">
          <h3>您可以尝试：</h3>
          <ul>
            <li>检查您的账户权限设置</li>
            <li>联系系统管理员申请访问权限</li>
            <li>确认您已正确登录系统</li>
            <li>返回首页查看其他可用功能</li>
          </ul>
        </div>
      </div>
      
      <!-- 装饰元素 -->
      <div class="error-decoration">
        <div class="decoration-circle circle-1"></div>
        <div class="decoration-circle circle-2"></div>
        <div class="decoration-circle circle-3"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  House,
  ArrowLeft,
  Service
} from '@element-plus/icons-vue'

const router = useRouter()

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

// 联系管理员
const contactAdmin = async () => {
  try {
    await ElMessageBox.alert(
      '请通过以下方式联系系统管理员：\n\n' +
      '• 邮箱：admin@company.com\n' +
      '• 电话：400-123-4567\n' +
      '• 工单系统：提交权限申请工单\n\n' +
      '请在联系时说明您需要访问的页面和具体用途。',
      '联系管理员',
      {
        confirmButtonText: '我知道了',
        type: 'info',
        customStyle: {
          'white-space': 'pre-line'
        }
      }
    )
  } catch {
    // 用户取消
  }
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
    filter: drop-shadow(0 10px 20px rgba(255, 77, 79, 0.3));
    animation: float 3s ease-in-out infinite;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

.error-info {
  margin-bottom: 40px;
  
  .error-title {
    font-size: 72px;
    font-weight: 700;
    color: #ff4d4f;
    margin: 0 0 10px 0;
    text-shadow: 0 4px 8px rgba(255, 77, 79, 0.3);
    animation: pulse 2s ease-in-out infinite;
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

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
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
  text-align: left;
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
  background: rgba(64, 158, 255, 0.1);
  border-radius: 12px;
  border-left: 4px solid #409eff;
  
  h3 {
    margin: 0 0 15px 0;
    color: #303133;
    font-size: 16px;
    font-weight: 600;
  }
  
  ul {
    margin: 0;
    padding-left: 20px;
    
    li {
      color: #606266;
      line-height: 1.6;
      margin-bottom: 8px;
      
      &:last-child {
        margin-bottom: 0;
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

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float-decoration 6s ease-in-out infinite;
  
  &.circle-1 {
    width: 100px;
    height: 100px;
    top: 10%;
    left: 10%;
    animation-delay: 0s;
  }
  
  &.circle-2 {
    width: 150px;
    height: 150px;
    top: 60%;
    right: 10%;
    animation-delay: 2s;
  }
  
  &.circle-3 {
    width: 80px;
    height: 80px;
    bottom: 20%;
    left: 20%;
    animation-delay: 4s;
  }
}

@keyframes float-decoration {
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
    opacity: 0.3;
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
    opacity: 0.6;
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
  
  .error-suggestions {
    text-align: center;
    
    ul {
      text-align: left;
    }
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
}
</style>