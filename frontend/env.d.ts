/// <reference types="vite/client" />
/// <reference types="vue/macros-global" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_BASE_API: string
  readonly VITE_APP_BASE_WS: string
  readonly VITE_APP_VERSION: string
  readonly VITE_APP_BUILD_TIME: string
  readonly VITE_APP_MOCK: string
  readonly VITE_APP_DEBUG: string
  readonly VITE_APP_UPLOAD_SIZE_LIMIT: string
  readonly VITE_APP_CHUNK_SIZE_LIMIT: string
  readonly VITE_APP_SEARCH_DEBOUNCE: string
  readonly VITE_APP_CACHE_EXPIRE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module '*.md' {
  const content: string
  export default content
}

declare module '*.json' {
  const content: any
  export default content
}

// Element Plus 自动导入类型声明
declare module '@vue/runtime-core' {
  export interface GlobalComponents {
    ElButton: typeof import('element-plus')['ElButton']
    ElInput: typeof import('element-plus')['ElInput']
    ElForm: typeof import('element-plus')['ElForm']
    ElFormItem: typeof import('element-plus')['ElFormItem']
    ElTable: typeof import('element-plus')['ElTable']
    ElTableColumn: typeof import('element-plus')['ElTableColumn']
    ElPagination: typeof import('element-plus')['ElPagination']
    ElDialog: typeof import('element-plus')['ElDialog']
    ElDrawer: typeof import('element-plus')['ElDrawer']
    ElCard: typeof import('element-plus')['ElCard']
    ElTabs: typeof import('element-plus')['ElTabs']
    ElTabPane: typeof import('element-plus')['ElTabPane']
    ElMenu: typeof import('element-plus')['ElMenu']
    ElMenuItem: typeof import('element-plus')['ElMenuItem']
    ElSubMenu: typeof import('element-plus')['ElSubMenu']
    ElBreadcrumb: typeof import('element-plus')['ElBreadcrumb']
    ElBreadcrumbItem: typeof import('element-plus')['ElBreadcrumbItem']
    ElDropdown: typeof import('element-plus')['ElDropdown']
    ElDropdownMenu: typeof import('element-plus')['ElDropdownMenu']
    ElDropdownItem: typeof import('element-plus')['ElDropdownItem']
    ElTooltip: typeof import('element-plus')['ElTooltip']
    ElPopover: typeof import('element-plus')['ElPopover']
    ElLoading: typeof import('element-plus')['ElLoading']
    ElMessage: typeof import('element-plus')['ElMessage']
    ElMessageBox: typeof import('element-plus')['ElMessageBox']
    ElNotification: typeof import('element-plus')['ElNotification']
  }
}

export {}