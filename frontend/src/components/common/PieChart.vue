<template>
  <div ref="chartRef" class="pie-chart"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  data: { name: string; value: number; color?: string }[]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  updateChart()
  
  // Use ResizeObserver to detect container size changes
  resizeObserver = new ResizeObserver(() => {
    chart?.resize()
  })
  resizeObserver.observe(chartRef.value)
}

const updateChart = () => {
  if (!chart) return
  const defaultColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
  
  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      top: 10,
      left: 'center',
      textStyle: { color: '#606266' }
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '58%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#ffffff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: { label: { show: false } },
      data: props.data.map((item, index) => ({
        name: item.name,
        value: item.value,
        itemStyle: { color: item.color || defaultColors[index % defaultColors.length] }
      }))
    }]
  }
  chart.setOption(option)
}

const handleResize = () => chart?.resize()

watch(() => props.data, updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

<style scoped>
.pie-chart {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
</style>
