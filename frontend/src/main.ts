import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

// 样式导入
import './styles/index.scss'

// 工具导入
// import { setupGlobalProperties } from './utils/global'
// 注释掉不存在的导入
// import { setupDirectives } from './directives'
// import { setupErrorHandler } from './utils/error-handler'
// import { setupPermissions } from './utils/permissions'

// 进度条
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 配置进度条
NProgress.configure({
  showSpinner: false,
  trickleSpeed: 200,
  minimum: 0.3
})

// 创建应用实例
const app = createApp(App)

// 创建 Pinia 状态管理
const pinia = createPinia()

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 获取当前语言设置
const getLocale = () => {
  const savedLocale = localStorage.getItem('locale')
  if (savedLocale) {
    return savedLocale === 'en' ? en : zhCn
  }
  
  // 根据浏览器语言自动选择
  const browserLang = navigator.language.toLowerCase()
  return browserLang.startsWith('en') ? en : zhCn
}

// 配置 Element Plus
app.use(ElementPlus, {
  locale: getLocale(),
  size: 'default',
  zIndex: 3000
})

// 使用插件
app.use(pinia)
app.use(router)

// 设置全局属性
// setupGlobalProperties(app)

// 设置自定义指令
// setupDirectives(app)

// 设置错误处理
// setupErrorHandler(app)

// 设置权限系统
// setupPermissions(app)

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('Global error:', err)
  console.error('Error info:', info)
  console.error('Component:', vm)
  
  // 可以在这里添加错误上报逻辑
  // errorReporter.report(err, { vm, info })
}

// 全局警告处理
app.config.warnHandler = (msg, vm, trace) => {
  console.warn('Global warning:', msg)
  console.warn('Component:', vm)
  console.warn('Trace:', trace)
}

// 性能监控
if (import.meta.env.DEV) {
  app.config.performance = true
}

// 挂载应用
app.mount('#app')

// 开发环境下的调试工具
if (import.meta.env.DEV) {
  // 将应用实例暴露到全局，方便调试
  ;(window as any).__VUE_APP__ = app
  
  // 性能监控
  if ('performance' in window) {
    window.addEventListener('load', () => {
      const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      console.log('App load time:', perfData.loadEventEnd - perfData.fetchStart, 'ms')
    })
  }
}

// 导出应用实例（用于测试）
export default app