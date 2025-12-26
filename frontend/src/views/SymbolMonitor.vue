<template>
  <div class="page-wrapper">
    <div class="page-toolbar">
      <div class="page-toolbar__left">
        <el-select-v2
          v-model="selectedSymbol"
          :options="symbolOptions"
          placeholder="搜索交易对"
          style="width: 200px"
          @change="fetchData"
          filterable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-select-v2>
        <el-radio-group v-model="interval" @change="fetchData" size="default">
          <el-radio-button value="15m">15m</el-radio-button>
          <el-radio-button value="30m">30m</el-radio-button>
          <el-radio-button value="1h">1H</el-radio-button>
          <el-radio-button value="4h">4H</el-radio-button>
          <el-radio-button value="1d">1D</el-radio-button>
          <el-radio-button value="3d">3D</el-radio-button>
        </el-radio-group>

      </div>
      <div class="page-toolbar__right">
        <el-radio-group v-model="viewMode" size="default">
          <el-radio-button value="chart">图表</el-radio-button>
          <el-radio-button value="table">列表</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="page-content" v-loading="loading">
      <el-empty v-if="!loading && !monitorData" description="暂无监控数据" />
      
      <template v-if="monitorData">
        <div class="overview-dashboard">
          <div class="metric-panel info-panel">
            <div class="info-header">
              <div class="symbol-info">
                <span class="symbol-name">{{ monitorData.symbol }}</span>
              </div>
            </div>
            <div class="kline-details" v-if="latestKline">
              <div class="detail-item">
                <span class="label">Open</span>
                <span class="value">{{ formatPrice(latestKline.open) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Close</span>
                <span class="value">{{ formatPrice(latestKline.close) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">High</span>
                <span class="value">{{ formatPrice(latestKline.high) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Low</span>
                <span class="value">{{ formatPrice(latestKline.low) }}</span>
              </div>
            </div>
          </div>

          <div class="metric-panel volume-panel" :class="{ triggered: monitorData.metrics.volume_triggered }">
            <div class="panel-title">
              <span class="label">成交量</span>
            </div>
            <div class="kline-details volume-grid">
              <div class="detail-item">
                <span class="label">15m Vol</span>
                <span class="value">{{ formatVolume(monitorData.metrics.volume_15m) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">8h Vol</span>
                <span class="value">{{ formatVolume(monitorData.metrics.volume_8h) }}</span>
              </div>
            </div>
            <div class="volume-progress-section">
              <div class="progress-info">
                <span class="label">Vol 占比</span>
                <span class="value">{{ ((monitorData.metrics.volume_15m / monitorData.metrics.volume_8h) * 100).toFixed(1) }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress" :style="{ width: Math.min((monitorData.metrics.volume_15m / monitorData.metrics.volume_8h) * 100 / monitorData.metrics.volume_percent * 100, 100) + '%' }"></div>
              </div>
            </div>
          </div>

          <div class="metric-panel rise-panel" :class="{ triggered: monitorData.metrics.rise_triggered }">
            <div class="panel-title">
              <span class="label">涨幅</span>
              <span class="open-time">{{ monitorData.metrics.rise_end_time || '-' }}</span>
            </div>
            <div class="kline-details volume-grid">
              <div class="detail-item">
                <span class="label">最近Close</span>
                <span class="value">{{ formatPrice(monitorData.metrics.rise_end_price || 0) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">15m前Open</span>
                <span class="value">{{ formatPrice(monitorData.metrics.rise_start_price || 0) }}</span>
              </div>
            </div>
            <div class="volume-progress-section">
              <div class="progress-info">
                <span class="label">涨幅</span>
                <span class="value" :class="{ 'text-success': monitorData.metrics.rise_percent > 0, 'text-danger': monitorData.metrics.rise_percent < 0 }">
                  {{ monitorData.metrics.rise_percent >= 0 ? '+' : '' }}{{ monitorData.metrics.rise_percent.toFixed(2) }}%
                </span>
              </div>
              <div class="progress-bar">
                <div class="progress" :style="{ width: Math.min(Math.abs(monitorData.metrics.rise_percent) / monitorData.metrics.rise_threshold * 100, 100) + '%' }"></div>
              </div>
            </div>
          </div>

          <div class="metric-panel open-panel" :class="{ triggered: monitorData.metrics.open_price_triggered }">
            <div class="panel-title">
              <span class="label">开盘价匹配</span>
              <span class="interval-tag">{{ interval }}</span>
              <span class="open-time">{{ monitorData.metrics.open_price_d_time || '-' }}</span>
            </div>
            <div class="kline-details volume-grid">
              <div class="detail-item">
                <span class="label">当前Open</span>
                <span class="value">{{ formatPrice(monitorData.metrics.open_price_d || 0) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">匹配Open</span>
                <span class="value">{{ monitorData.metrics.open_price_e ? formatPrice(monitorData.metrics.open_price_e) : '-' }}</span>
              </div>
            </div>
            <div class="kline-details volume-grid no-border">
              <div class="detail-item">
                <span class="label">价格误差</span>
                <span class="value" :class="{ 'text-danger': monitorData.metrics.open_price_triggered }">
                  {{ monitorData.metrics.open_price_error != null ? monitorData.metrics.open_price_error.toFixed(2) + '%' : '-' }}
                </span>
              </div>
              <div class="detail-item">
                <span class="label">匹配时间</span>
                <span class="value" :class="{ 'text-danger': monitorData.metrics.open_price_triggered }">
                  {{ monitorData.metrics.open_price_e_time || '-' }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="kline-section">
          <div v-show="viewMode === 'chart'" class="kline-chart-wrapper" ref="klineWrapperRef">
            <div class="kline-chart" ref="chartRef"></div>
          </div>
          
          <div v-if="viewMode === 'table'" class="kline-table">
            <el-table :data="monitorData.klines" :default-sort="{ prop: 'open', order: 'descending' }" size="small" height="100%" style="width: 100%">
              <el-table-column prop="open_time" label="open_time" width="160" sortable />
              <el-table-column prop="open" label="open" sortable><template #default="{ row }">{{ formatPrice(row.open) }}</template></el-table-column>
              <el-table-column prop="high" label="high" sortable><template #default="{ row }">{{ formatPrice(row.high) }}</template></el-table-column>
              <el-table-column prop="low" label="low" sortable><template #default="{ row }">{{ formatPrice(row.low) }}</template></el-table-column>
              <el-table-column prop="close" label="close" sortable><template #default="{ row }">{{ formatPrice(row.close) }}</template></el-table-column>
              <el-table-column prop="volume" label="volume" sortable><template #default="{ row }">{{ formatVolume(row.volume) }}</template></el-table-column>
              <el-table-column prop="close_time" label="close_time" width="160" sortable />
              <el-table-column prop="quote_volume" label="quote_volume" sortable><template #default="{ row }">{{ formatVolume(row.quote_volume) }}</template></el-table-column>
            </el-table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, inject, computed } from 'vue'
import * as echarts from 'echarts'
import { getSymbolMonitorData, getSymbols, createEventSource } from '@/api'
import type { SymbolMonitorData } from '@/types'
import type { SSEEvent } from '@/api'
import { Search } from '@element-plus/icons-vue'
import { logger } from '@/utils/logger'

const loading = ref(false)
const selectedSymbol = ref('')
const symbolOptions = ref<{ label: string; value: string }[]>([])
const monitorData = ref<SymbolMonitorData | null>(null)
const interval = ref('15m')
const viewMode = ref<'chart' | 'table'>('chart')
const chartRef = ref<HTMLElement | null>(null)
const klineWrapperRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const latestKline = computed(() => {
  if (!monitorData.value || !monitorData.value.klines.length) return null
  return monitorData.value.klines[monitorData.value.klines.length - 1]
})

let resizeObserver: ResizeObserver | null = null
let eventSource: EventSource | null = null

const registerRefreshCallback = inject<(cb: () => Promise<void>) => void>('registerRefreshCallback')
const unregisterRefreshCallback = inject<(cb: () => Promise<void>) => void>('unregisterRefreshCallback')

const refreshCallback = async () => { await fetchData() }

const formatPrice = (price: number): string => {
  if (price >= 1000) return price.toFixed(2)
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}

const formatVolume = (volume: number): string => {
  return volume.toLocaleString('en-US', { maximumFractionDigits: 3 })
}

const loadSymbolOptions = async () => {
  try {
    const response = await getSymbols({ is_active: true, limit: 1000 })
    symbolOptions.value = response.items.map(item => ({ label: item.symbol, value: item.symbol }))
    if (symbolOptions.value.length > 0 && !selectedSymbol.value) selectedSymbol.value = symbolOptions.value[0].value
  } catch (error) {
    logger.error('获取交易对列表失败', error, { sampling: 10000 })
  }
}

const fetchData = async () => {
  if (!selectedSymbol.value) return
  loading.value = true
  try {
    monitorData.value = await getSymbolMonitorData(selectedSymbol.value, interval.value, 100)
    await nextTick()
    renderChart()
  } catch (error) {
    logger.error('获取监控数据失败', error, { 
      sampling: 5000,
      context: { symbol: selectedSymbol.value, interval: interval.value }
    })
  } finally {
    loading.value = false
  }
}

const renderChart = () => {
  if (viewMode.value !== 'chart' || !chartRef.value || !monitorData.value) return
  if (chartInstance) chartInstance.dispose()
  
  const chart = echarts.init(chartRef.value)
  chartInstance = chart
  
  const klines = monitorData.value.klines
  const dates = klines.map(k => k.open_time)
  const ohlc = klines.map(k => [k.open, k.close, k.low, k.high])
  const volumes = klines.map(k => k.quote_volume)
  
  const upColor = '#67c23a'
  const downColor = '#f56c6c'
  
  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, padding: 4, textStyle: { fontSize: 12 } },
    grid: [
      { left: '5%', right: '5%', top: '5%', height: '60%' },
      { left: '5%', right: '5%', top: '70%', height: '25%' }
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false } }
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, scale: true, splitLine: { show: false }, axisLabel: { show: false } },
      { type: 'value', gridIndex: 1, scale: true, splitLine: { show: false }, axisLabel: { show: false } }
    ],
    series: [
      { name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: upColor, color0: downColor, borderColor: upColor, borderColor0: downColor } },
      { name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: (params: any) => ohlc[params.dataIndex][1] >= ohlc[params.dataIndex][0] ? 'rgba(103, 194, 58, 0.4)' : 'rgba(245, 108, 108, 0.4)' } }
    ]
  }
  chart.setOption(option)
}

watch(viewMode, async () => { await nextTick(); renderChart() })

const handleResize = () => chartInstance?.resize()

const setupResizeObserver = () => {
  if (resizeObserver) resizeObserver.disconnect()
  resizeObserver = new ResizeObserver(() => handleResize())
  if (klineWrapperRef.value) resizeObserver.observe(klineWrapperRef.value)
}

const handleSSEEvent = (event: SSEEvent) => {
  if (event.type === 'sync_complete' || event.type === 'monitor_complete') fetchData()
}

onMounted(async () => {
  await loadSymbolOptions()
  fetchData()
  registerRefreshCallback?.(refreshCallback)
  eventSource = createEventSource(handleSSEEvent)
  window.addEventListener('resize', handleResize)
  await nextTick()
  setupResizeObserver()
})

onUnmounted(() => {
  unregisterRefreshCallback?.(refreshCallback)
  if (eventSource) { eventSource.close(); eventSource = null }
  if (resizeObserver) resizeObserver.disconnect()
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.page-wrapper {
  height: calc(100vh - var(--header-height));
  overflow: hidden;
}
.page-toolbar__left { gap: var(--spacing-md); }
.page-content { display: flex; flex-direction: column; gap: var(--spacing-lg); flex: 1; min-height: 0; overflow: hidden; }

.overview-dashboard { 
  display: grid; 
  grid-template-columns: repeat(4, 1fr); 
  gap: var(--spacing-md); 
  flex-shrink: 0; 
}

.symbol-info { display: flex; flex-direction: row; justify-content: space-between; align-items: center; width: 100%; }
.symbol-name { font-size: var(--font-size-md); font-weight: var(--font-weight-bold); color: var(--text-color-primary); }

.kline-details { 
  display: grid; 
  grid-template-columns: repeat(2, 1fr); 
  gap: var(--spacing-sm) var(--spacing-md); 
  padding-top: var(--spacing-sm); 
  border-top: 1px solid var(--border-color-lighter); 
}
.kline-details.no-border { border-top: none; padding-top: 0; }
.detail-item { display: flex; flex-direction: column; gap: 2px; }
.detail-item .label { font-size: var(--font-size-xs); color: var(--text-color-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.detail-item .value { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--text-color-primary); font-family: var(--font-family-monospace); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.metric-panel { 
  height: 160px; 
  background: var(--bg-color-overlay); 
  border-radius: var(--radius-lg); 
  padding: var(--spacing-md); 
  display: flex; 
  flex-direction: column; 
  gap: var(--spacing-sm); 
  border: 1px solid var(--border-color-lighter); 
  box-shadow: var(--shadow-sm); 
  transition: all 0.3s ease; 
}

.metric-panel:hover { box-shadow: var(--shadow-md); }

.info-panel { flex-direction: column; justify-content: flex-start; align-items: stretch; gap: var(--spacing-sm); }
.info-header { display: flex; justify-content: space-between; align-items: center; }

.metric-panel.triggered { 
  border-color: var(--el-color-danger); 
  background: rgba(245, 108, 108, 0.05); 
}

.panel-title { display: flex; justify-content: space-between; align-items: center; font-size: var(--font-size-sm); color: var(--text-color-regular); }
.panel-title .label { font-size: var(--font-size-md); font-weight: var(--font-weight-bold); color: var(--text-color-primary); }
.panel-title .label { margin-right: auto; }
.panel-title .interval-tag { font-size: var(--font-size-xs); color: var(--text-color-secondary); background: var(--bg-color-page); padding: 2px 8px; border-radius: var(--radius-sm); margin-left: 8px; }
.panel-title .open-time { font-size: var(--font-size-xs); color: var(--text-color-secondary); margin-left: 8px; }

.panel-content { display: flex; flex-direction: column; gap: 4px; }
.data-row { display: flex; justify-content: space-between; font-size: var(--font-size-sm); color: var(--text-color-secondary); }
.data-row strong { color: var(--text-color-primary); font-weight: var(--font-weight-semibold); }

.progress-bar { height: 3px; background: var(--border-color-light); border-radius: 2px; margin-top: 4px; overflow: hidden; }
.progress { height: 100%; background: var(--el-color-primary); border-radius: 2px; }
.triggered .progress { background: var(--el-color-danger); }

.center-align { align-items: center; justify-content: center; padding: 8px 0; }
.big-stat { font-size: 18px; font-weight: var(--font-weight-bold); }
.sub-stat { font-size: var(--font-size-xs); color: var(--text-color-secondary); }

.text-success { color: var(--el-color-success); }
.text-danger { color: var(--el-color-danger); }
.match-info { font-size: var(--font-size-xs); color: var(--el-color-danger); margin-top: 6px; padding-top: 6px; border-top: 1px dashed var(--border-color-light); word-break: break-all; }

.volume-grid {
  margin-bottom: 0;
}
.volume-progress-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-xs);
}
.progress-info .label { color: var(--text-color-secondary); }
.progress-info .value { font-weight: var(--font-weight-semibold); color: var(--text-color-primary); }

.kline-section { 
  flex: 1; 
  min-height: 0; 
  display: flex; 
  flex-direction: column; 
  background: var(--bg-color-overlay); 
  border-radius: var(--radius-lg); 
  padding: var(--spacing-md); 
  border: 1px solid var(--border-color-lighter); 
  box-shadow: var(--shadow-sm); 
}

.kline-chart-wrapper { flex: 1; width: 100%; min-height: 0; position: relative; }
.kline-chart { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.kline-table { flex: 1; min-height: 0; }
</style>
