<template>
  <div class="line-chart" :style="{ width: width, height: height }">
    <div ref="chartRef" :style="{ width: '100%', height: '100%' }"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

// 接口定义
interface LineDataItem {
  name: string
  value: number | [string, number]
}

interface SeriesData {
  name: string
  data: LineDataItem[]
  color?: string
  type?: 'line' | 'bar'
  smooth?: boolean
  areaStyle?: any
}

interface Props {
  data: SeriesData[]
  xAxisData?: string[]
  title?: string
  width?: string
  height?: string
  showLegend?: boolean
  showGrid?: boolean
  smooth?: boolean
  area?: boolean
  colors?: string[]
  yAxisName?: string
  xAxisName?: string
}

// Props
const props = withDefaults(defineProps<Props>(), {
  title: '',
  width: '100%',
  height: '300px',
  showLegend: true,
  showGrid: true,
  smooth: false,
  area: false,
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
  ],
  yAxisName: '',
  xAxisName: ''
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
  
  // 处理 X 轴数据
  let xAxisData = props.xAxisData
  if (!xAxisData && props.data.length > 0) {
    // 从第一个系列中提取 X 轴数据
    xAxisData = props.data[0].data.map(item => 
      typeof item.value === 'object' ? item.value[0] : item.name
    )
  }
  
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
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      backgroundColor: 'rgba(50, 50, 50, 0.9)',
      borderColor: 'transparent',
      textStyle: {
        color: '#fff'
      }
    },
    legend: {
      show: props.showLegend,
      data: props.data.map(series => series.name),
      top: props.title ? 30 : 10,
      textStyle: {
        color: '#606266'
      }
    },
    grid: {
      show: props.showGrid,
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: props.showLegend ? (props.title ? 60 : 40) : (props.title ? 40 : 20),
      containLabel: true,
      borderColor: '#e4e7ed'
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      name: props.xAxisName,
      nameTextStyle: {
        color: '#909399'
      },
      axisLine: {
        lineStyle: {
          color: '#e4e7ed'
        }
      },
      axisLabel: {
        color: '#606266'
      }
    },
    yAxis: {
      type: 'value',
      name: props.yAxisName,
      nameTextStyle: {
        color: '#909399'
      },
      axisLine: {
        lineStyle: {
          color: '#e4e7ed'
        }
      },
      axisLabel: {
        color: '#606266'
      },
      splitLine: {
        lineStyle: {
          color: '#f5f7fa'
        }
      }
    },
    color: props.colors,
    series: props.data.map((series, index) => ({
      name: series.name,
      type: series.type || 'line',
      smooth: series.smooth !== undefined ? series.smooth : props.smooth,
      data: series.data.map(item => 
        typeof item.value === 'object' ? item.value[1] : item.value
      ),
      itemStyle: {
        color: series.color || props.colors[index % props.colors.length]
      },
      lineStyle: {
        width: 2
      },
      symbol: 'circle',
      symbolSize: 6,
      areaStyle: (props.area || series.areaStyle) ? {
        opacity: 0.3
      } : undefined,
      emphasis: {
        focus: 'series'
      }
    }))
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
  () => [props.data, props.xAxisData, props.title, props.showLegend, props.showGrid, props.smooth, props.area, props.colors],
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
.line-chart {
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