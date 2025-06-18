<template>
  <div class="pie-chart" :style="{ width: width, height: height }">
    <div ref="chartRef" :style="{ width: '100%', height: '100%' }"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

// 接口定义
interface PieDataItem {
  name: string
  value: number
  itemStyle?: {
    color?: string
  }
}

interface Props {
  data: PieDataItem[]
  title?: string
  width?: string
  height?: string
  showLegend?: boolean
  showLabel?: boolean
  radius?: string | [string, string]
  center?: [string, string]
  colors?: string[]
}

// Props
const props = withDefaults(defineProps<Props>(), {
  title: '',
  width: '100%',
  height: '300px',
  showLegend: true,
  showLabel: true,
  radius: '60%',
  center: () => ['50%', '50%'] as [string, string],
  colors: () => [
    '#5470c6',
    '#91cc75',
    '#fac858',
    '#ee6666',
    '#73c0de',
    '#3ba272',
    '#fc8452',
    '#9a60b4',
    '#ea7ccc'
  ]
})

// 响应式数据
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) return
  
  const option: echarts.EChartsOption = {
    title: {
      text: props.title,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal',
        color: '#303133'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      show: props.showLegend,
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      textStyle: {
        color: '#606266'
      }
    },
    color: props.colors,
    series: [
      {
        name: props.title || '数据统计',
        type: 'pie',
        radius: props.radius,
        center: props.center,
        data: props.data.map((item, index) => ({
          ...item,
          itemStyle: {
            color: item.itemStyle?.color || props.colors[index % props.colors.length]
          }
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        label: {
          show: props.showLabel,
          formatter: '{b}: {d}%',
          color: '#606266'
        },
        labelLine: {
          show: props.showLabel
        }
      }
    ]
  }
  
  chartInstance.setOption(option, true)
}

// 调整图表大小
const resizeChart = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// 监听数据变化
watch(
  () => [props.data, props.title, props.showLegend, props.showLabel, props.radius, props.center, props.colors],
  () => {
    nextTick(() => {
      updateChart()
    })
  },
  { deep: true }
)

// 监听窗口大小变化
const handleResize = () => {
  resizeChart()
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
  })
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  
  window.removeEventListener('resize', handleResize)
})

// 暴露方法
defineExpose({
  resize: resizeChart,
  getInstance: () => chartInstance
})
</script>

<style scoped lang="scss">
.pie-chart {
  position: relative;
  
  &:deep(.echarts-tooltip) {
    background-color: rgba(50, 50, 50, 0.9) !important;
    border: none !important;
    border-radius: 4px !important;
    color: #fff !important;
    font-size: 12px !important;
    padding: 8px 12px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
  }
}
</style>