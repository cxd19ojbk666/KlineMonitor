<template>
  <div class="page-wrapper--card">
    <el-row :gutter="24" class="stat-cards">
      <el-col :span="6" v-for="(card, index) in statCards" :key="index">
        <StatCard
          :title="card.title"
          :value="card.value"
          :color="card.color"
          class="animate-up"
          :style="{ animationDelay: `${index * 0.1}s` }"
        />
      </el-col>
    </el-row>

    <el-row :gutter="24" class="content-row">
      <el-col :span="16">
        <el-card class="alert-card" body-style="padding: 0">
          <template #header>
            <div class="card-header">
              <div class="card-header__title">
                <span>最近提醒记录</span>
              </div>
            </div>
          </template>
          <div class="alert-list-container">
            <el-scrollbar>
              <div class="alert-items-grid" v-if="stats.recent_alerts && stats.recent_alerts.length > 0">
                <div v-for="alert in stats.recent_alerts" :key="alert.id" class="card-grid__item--compact">
                  <AlertCard :alert="alert">
                    <template #actions>
                      <el-button type="info" link size="small" class="delete-btn" @click="handleDelete(alert.id)">
                        <el-icon :size="18"><Delete /></el-icon>
                      </el-button>
                    </template>
                  </AlertCard>
                </div>
              </div>
              <div v-else class="empty-alert">
                <el-empty description="暂无提醒记录" :image-size="100" />
              </div>
            </el-scrollbar>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8" class="right-column">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <div class="card-header__title">
                <span>提醒类型分布</span>
              </div>
            </div>
          </template>
          <PieChart :data="pieData" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, PieChart as PieChartIcon, Delete } from '@element-plus/icons-vue'
import { getDashboard, deleteAlert, createEventSource } from '@/api'
import type { DashboardStats } from '@/types'
import type { SSEEvent } from '@/api'
import StatCard from '@/components/common/StatCard.vue'
import PieChart from '@/components/common/PieChart.vue'
import AlertCard from '@/components/alert/AlertCard.vue'
import { logger } from '@/utils/logger'
import { confirmDelete } from '@/utils/confirm'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()

const stats = ref<DashboardStats>({
  total_alerts_today: 0,
  alert_type_1_count: 0,
  alert_type_2_count: 0,
  alert_type_3_count: 0,
  is_running: false,
  recent_alerts: []
})

let eventSource: EventSource | null = null

const registerRefreshCallback = inject<(cb: () => Promise<void>) => void>('registerRefreshCallback')
const unregisterRefreshCallback = inject<(cb: () => Promise<void>) => void>('unregisterRefreshCallback')

const refreshCallback = async () => {
  await fetchData()
  ElMessage.success('刷新成功')
}

const statCards = computed(() => [
  { title: '今日提醒总数', value: stats.value.total_alerts_today, color: '#1967d2' },
  { title: '成交量提醒', value: stats.value.alert_type_1_count, color: '#e6a23c' },
  { title: '涨幅提醒', value: stats.value.alert_type_2_count, color: '#f56c6c' },
  { title: '开盘价匹配', value: stats.value.alert_type_3_count, color: '#67c23a' }
])

const pieData = computed(() => [
  { name: '成交量提醒', value: stats.value.alert_type_1_count, color: '#e6a23c' },
  { name: '涨幅提醒', value: stats.value.alert_type_2_count, color: '#f56c6c' },
  { name: '开盘价匹配', value: stats.value.alert_type_3_count, color: '#67c23a' }
])

const fetchData = async () => {
  try {
    stats.value = await getDashboard()
  } catch (error) {
    logger.error('获取仪表盘数据失败', error, { sampling: 5000 })
  }
}

const handleDelete = (id: number) => {
  ElMessageBox.confirm(
    '确定要删除这条记录吗?',
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      showClose: false
    }
  )
    .then(async () => {
      try {
        await deleteAlert(id)
        ElMessage.success('删除成功')
        fetchData()
      } catch {
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {})
}

const handleSSEEvent = (event: SSEEvent) => {
  if (event.type === 'sync_complete' || event.type === 'monitor_complete') fetchData()
}

onMounted(() => {
  fetchData()
  registerRefreshCallback?.(refreshCallback)
  eventSource = createEventSource(handleSSEEvent)
})

// 监听配置变更，自动刷新提示卡片数据
watch(() => configStore.configVersion, () => {
  fetchData()
})

onUnmounted(() => {
  unregisterRefreshCallback?.(refreshCallback)
  if (eventSource) { eventSource.close(); eventSource = null }
})
</script>

<style scoped>
.stat-cards { margin-bottom: 0; flex-shrink: 0; }
.content-row { display: flex; align-items: stretch; flex: 1; min-height: 0; }
.el-col { height: 100%; }
.right-column { display: flex; flex-direction: column; gap: 24px; height: 100%; }

.alert-card { height: 100%; display: flex; flex-direction: column; }
.alert-card :deep(.el-card__body) { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 0; }
.alert-list-container { flex: 1; height: 100%; overflow: hidden; padding: var(--spacing-md); background-color: var(--bg-color-overlay); }
.alert-items-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--spacing-md); padding-bottom: var(--spacing-md); }
.empty-alert { height: 100%; display: flex; align-items: center; justify-content: center; }

.chart-card { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.chart-card :deep(.el-card__body) { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; }
</style>
