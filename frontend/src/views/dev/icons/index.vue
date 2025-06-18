<template>
  <div class="dev-icons">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <h2>图标库</h2>
          <p>Element Plus 图标库展示和使用示例</p>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="search-section">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索图标名称"
              prefix-icon="Search"
              clearable
            />
          </el-col>
          <el-col :span="6">
            <el-select v-model="selectedCategory" placeholder="选择分类" clearable>
              <el-option label="全部" value="" />
              <el-option label="基础图标" value="basic" />
              <el-option label="方向图标" value="direction" />
              <el-option label="媒体图标" value="media" />
              <el-option label="文件图标" value="file" />
              <el-option label="编辑图标" value="edit" />
              <el-option label="系统图标" value="system" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-input-number
              v-model="iconSize"
              :min="16"
              :max="64"
              controls-position="right"
              style="width: 100%"
            />
            <span style="margin-left: 8px; color: #909399;">图标大小</span>
          </el-col>
        </el-row>
      </div>

      <!-- 使用说明 -->
      <div class="usage-section">
        <el-alert
          title="使用说明"
          type="info"
          :closable="false"
          show-icon
        >
          <template #default>
            <p>1. 点击图标可复制其名称到剪贴板</p>
            <p>2. 在 Vue 模板中使用：<code>&lt;el-icon&gt;&lt;IconName /&gt;&lt;/el-icon&gt;</code></p>
            <p>3. 需要先导入图标：<code>import { IconName } from '@element-plus/icons-vue'</code></p>
          </template>
        </el-alert>
      </div>

      <!-- 图标展示 -->
      <div class="icons-section">
        <div class="icons-grid">
          <div
            v-for="icon in filteredIcons"
            :key="icon.name"
            class="icon-item"
            @click="copyIconName(icon.name)"
          >
            <div class="icon-display">
              <component :is="icon.component" :size="iconSize" />
            </div>
            <div class="icon-name">{{ icon.name }}</div>
          </div>
        </div>
        
        <div v-if="filteredIcons.length === 0" class="no-results">
          <el-empty description="没有找到匹配的图标" />
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-section" v-if="filteredIcons.length > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 40, 60, 100]"
          :total="filteredIcons.length"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  // 基础图标
  Search,
  Edit,
  Delete,
  Plus,
  Minus,
  Close,
  Check,
  Star,
  StarFilled,
  // Heart, // 不存在于 @element-plus/icons-vue
  // 方向图标
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  CaretTop,
  CaretBottom,
  CaretLeft,
  CaretRight,
  // 媒体图标
  VideoPlay,
  VideoPause,
  Microphone,
  // MicrophoneFilled, // 不存在，建议使用 Microphone
  Camera,
  CameraFilled,
  Picture,
  PictureFilled,
  // 文件图标
  Document,
  DocumentCopy,
  Folder,
  FolderOpened,
  Files,
  Download,
  Upload,
  // 编辑图标
  EditPen,
  // Scissors, // 不存在于 @element-plus/icons-vue
  CopyDocument,
  Share,
  Link,
  Paperclip,
  // 系统图标
  Setting,
  Tools,
  Monitor,
  Cpu,
  // MemoryCard, // 不存在于 @element-plus/icons-vue
  // HardDisk, // 不存在于 @element-plus/icons-vue
  User,
  UserFilled,
  Lock,
  Unlock,
  View,
  Hide,
  Bell,
  BellFilled,
  Message,
  MessageBox,
  Phone,
  PhoneFilled,
  Location,
  LocationFilled,
  Calendar,
  Clock,
  Timer,
  Stopwatch,
  Flag,
  Trophy,
  Medal,
  // Gift, // 不存在于 @element-plus/icons-vue
  ShoppingCart,
  ShoppingBag,
  Coin,
  Money,
  CreditCard,
  Wallet,
  House,
  OfficeBuilding, // 修正：Office -> OfficeBuilding
  School,
  // Hospital, // 不存在于 @element-plus/icons-vue
  // Restaurant, // 不存在于 @element-plus/icons-vue
  Coffee,
  IceCream,
  Orange,
  Apple,
  Pear,
  Watermelon,
  Cherry,
  Grape,
  // 更多图标
  Refresh,
  Loading,
  More,
  MoreFilled,
  Grid,
  List,
  Menu,
  Operation,
  Expand,
  Fold,
  SortUp,
  SortDown,
  Rank,
  Filter,
  ZoomIn,
  ZoomOut,
  FullScreen,
  ScaleToOriginal,
  DCaret,
  Back,
  Right,
  Bottom,
  Top
} from '@element-plus/icons-vue'

// 图标数据接口
interface IconItem {
  name: string
  component: any
  category: string
}

// 响应式数据
const searchKeyword = ref('')
const selectedCategory = ref('')
const iconSize = ref(24)
const currentPage = ref(1)
const pageSize = ref(60)

// 图标数据
const icons = ref<IconItem[]>([
  // 基础图标
  { name: 'Search', component: Search, category: 'basic' },
  { name: 'Edit', component: Edit, category: 'basic' },
  { name: 'Delete', component: Delete, category: 'basic' },
  { name: 'Plus', component: Plus, category: 'basic' },
  { name: 'Minus', component: Minus, category: 'basic' },
  { name: 'Close', component: Close, category: 'basic' },
  { name: 'Check', component: Check, category: 'basic' },
  { name: 'Star', component: Star, category: 'basic' },
  { name: 'StarFilled', component: StarFilled, category: 'basic' },
  // { name: 'Heart', component: Heart, category: 'basic' }, // 图标不存在
  
  // 方向图标
  { name: 'ArrowUp', component: ArrowUp, category: 'direction' },
  { name: 'ArrowDown', component: ArrowDown, category: 'direction' },
  { name: 'ArrowLeft', component: ArrowLeft, category: 'direction' },
  { name: 'ArrowRight', component: ArrowRight, category: 'direction' },
  { name: 'CaretTop', component: CaretTop, category: 'direction' },
  { name: 'CaretBottom', component: CaretBottom, category: 'direction' },
  { name: 'CaretLeft', component: CaretLeft, category: 'direction' },
  { name: 'CaretRight', component: CaretRight, category: 'direction' },
  { name: 'Back', component: Back, category: 'direction' },
  { name: 'Right', component: Right, category: 'direction' },
  { name: 'Bottom', component: Bottom, category: 'direction' },
  { name: 'Top', component: Top, category: 'direction' },
  
  // 媒体图标
  { name: 'VideoPlay', component: VideoPlay, category: 'media' },
  { name: 'VideoPause', component: VideoPause, category: 'media' },
  { name: 'Microphone', component: Microphone, category: 'media' },
  // { name: 'MicrophoneFilled', component: MicrophoneFilled, category: 'media' }, // 图标不存在
  { name: 'Camera', component: Camera, category: 'media' },
  { name: 'CameraFilled', component: CameraFilled, category: 'media' },
  { name: 'Picture', component: Picture, category: 'media' },
  { name: 'PictureFilled', component: PictureFilled, category: 'media' },
  
  // 文件图标
  { name: 'Document', component: Document, category: 'file' },
  { name: 'DocumentCopy', component: DocumentCopy, category: 'file' },
  { name: 'Folder', component: Folder, category: 'file' },
  { name: 'FolderOpened', component: FolderOpened, category: 'file' },
  { name: 'Files', component: Files, category: 'file' },
  { name: 'Download', component: Download, category: 'file' },
  { name: 'Upload', component: Upload, category: 'file' },
  
  // 编辑图标
  { name: 'EditPen', component: EditPen, category: 'edit' },
  // { name: 'Scissors', component: Scissors, category: 'edit' }, // 图标不存在
  { name: 'CopyDocument', component: CopyDocument, category: 'edit' },
  { name: 'Share', component: Share, category: 'edit' },
  { name: 'Link', component: Link, category: 'edit' },
  { name: 'Paperclip', component: Paperclip, category: 'edit' },
  
  // 系统图标
  { name: 'Setting', component: Setting, category: 'system' },
  { name: 'Tools', component: Tools, category: 'system' },
  { name: 'Monitor', component: Monitor, category: 'system' },
  { name: 'Cpu', component: Cpu, category: 'system' },
  // { name: 'MemoryCard', component: MemoryCard, category: 'system' }, // 图标不存在
  // { name: 'HardDisk', component: HardDisk, category: 'system' }, // 图标不存在
  { name: 'User', component: User, category: 'system' },
  { name: 'UserFilled', component: UserFilled, category: 'system' },
  { name: 'Lock', component: Lock, category: 'system' },
  { name: 'Unlock', component: Unlock, category: 'system' },
  { name: 'View', component: View, category: 'system' },
  { name: 'Hide', component: Hide, category: 'system' },
  { name: 'Bell', component: Bell, category: 'system' },
  { name: 'BellFilled', component: BellFilled, category: 'system' },
  { name: 'Message', component: Message, category: 'system' },
  { name: 'MessageBox', component: MessageBox, category: 'system' },
  { name: 'Phone', component: Phone, category: 'system' },
  { name: 'PhoneFilled', component: PhoneFilled, category: 'system' },
  { name: 'Location', component: Location, category: 'system' },
  { name: 'LocationFilled', component: LocationFilled, category: 'system' },
  { name: 'Calendar', component: Calendar, category: 'system' },
  { name: 'Clock', component: Clock, category: 'system' },
  { name: 'Timer', component: Timer, category: 'system' },
  { name: 'Stopwatch', component: Stopwatch, category: 'system' },
  { name: 'Flag', component: Flag, category: 'system' },
  { name: 'Trophy', component: Trophy, category: 'system' },
  { name: 'Medal', component: Medal, category: 'system' },
  // { name: 'Gift', component: Gift, category: 'system' }, // 图标不存在
  { name: 'ShoppingCart', component: ShoppingCart, category: 'system' },
  { name: 'ShoppingBag', component: ShoppingBag, category: 'system' },
  { name: 'Coin', component: Coin, category: 'system' },
  { name: 'Money', component: Money, category: 'system' },
  { name: 'CreditCard', component: CreditCard, category: 'system' },
  { name: 'Wallet', component: Wallet, category: 'system' },
  { name: 'House', component: House, category: 'system' },
  { name: 'OfficeBuilding', component: OfficeBuilding, category: 'system' }, // 修正：Office -> OfficeBuilding
  { name: 'School', component: School, category: 'system' },
  // { name: 'Hospital', component: Hospital, category: 'system' }, // 图标不存在
  // { name: 'Restaurant', component: Restaurant, category: 'system' }, // 图标不存在
  { name: 'Coffee', component: Coffee, category: 'system' },
  { name: 'IceCream', component: IceCream, category: 'system' },
  { name: 'Orange', component: Orange, category: 'system' },
  { name: 'Apple', component: Apple, category: 'system' },
  { name: 'Pear', component: Pear, category: 'system' },
  { name: 'Watermelon', component: Watermelon, category: 'system' },
  { name: 'Cherry', component: Cherry, category: 'system' },
  { name: 'Grape', component: Grape, category: 'system' },
  { name: 'Refresh', component: Refresh, category: 'system' },
  { name: 'Loading', component: Loading, category: 'system' },
  { name: 'More', component: More, category: 'system' },
  { name: 'MoreFilled', component: MoreFilled, category: 'system' },
  { name: 'Grid', component: Grid, category: 'system' },
  { name: 'List', component: List, category: 'system' },
  { name: 'Menu', component: Menu, category: 'system' },
  { name: 'Operation', component: Operation, category: 'system' },
  { name: 'Expand', component: Expand, category: 'system' },
  { name: 'Fold', component: Fold, category: 'system' },
  { name: 'SortUp', component: SortUp, category: 'system' },
  { name: 'SortDown', component: SortDown, category: 'system' },
  { name: 'Rank', component: Rank, category: 'system' },
  { name: 'Filter', component: Filter, category: 'system' },
  { name: 'ZoomIn', component: ZoomIn, category: 'system' },
  { name: 'ZoomOut', component: ZoomOut, category: 'system' },
  { name: 'FullScreen', component: FullScreen, category: 'system' },
  { name: 'ScaleToOriginal', component: ScaleToOriginal, category: 'system' },
  { name: 'DCaret', component: DCaret, category: 'system' }
])

// 计算属性
const filteredIcons = computed(() => {
  let result = icons.value
  
  // 按关键词筛选
  if (searchKeyword.value) {
    result = result.filter(icon => 
      icon.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }
  
  // 按分类筛选
  if (selectedCategory.value) {
    result = result.filter(icon => icon.category === selectedCategory.value)
  }
  
  // 分页
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return result.slice(start, end)
})

// 方法
const copyIconName = async (iconName: string) => {
  try {
    await navigator.clipboard.writeText(iconName)
    ElMessage.success(`图标名称 "${iconName}" 已复制到剪贴板`)
  } catch (error) {
    // 降级方案
    const textArea = document.createElement('textarea')
    textArea.value = iconName
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    ElMessage.success(`图标名称 "${iconName}" 已复制到剪贴板`)
  }
}

// 生命周期
onMounted(() => {
  console.log('图标库页面已加载，共', icons.value.length, '个图标')
})
</script>

<style scoped lang="scss">
.dev-icons {
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

  .search-section {
    margin: 20px 0;
  }

  .usage-section {
    margin: 20px 0;

    code {
      background-color: #f5f7fa;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      color: #e6a23c;
    }

    p {
      margin: 5px 0;
    }
  }

  .icons-section {
    margin: 20px 0;

    .icons-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 15px;
      margin-bottom: 20px;

      .icon-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 15px 10px;
        border: 1px solid #ebeef5;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.3s ease;
        background-color: #fff;

        &:hover {
          border-color: #409eff;
          box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
          transform: translateY(-2px);
        }

        .icon-display {
          margin-bottom: 8px;
          color: #606266;
          transition: color 0.3s ease;
        }

        .icon-name {
          font-size: 12px;
          color: #909399;
          text-align: center;
          word-break: break-all;
          line-height: 1.4;
        }

        &:hover {
          .icon-display {
            color: #409eff;
          }

          .icon-name {
            color: #409eff;
          }
        }
      }
    }

    .no-results {
      text-align: center;
      padding: 40px 0;
    }
  }

  .pagination-section {
    margin: 20px 0;
    text-align: center;
  }
}

:deep(.el-alert__content) {
  p {
    margin: 5px 0;
  }
}
</style>