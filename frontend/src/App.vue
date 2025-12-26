<template>
  <el-container class="app-layout">
    <AppSidebar :is-collapsed="isSidebarCollapsed" @toggle-collapse="toggleSidebar" />

    <el-container class="main-wrapper">
      <el-header class="app-header">
        <div class="header-section section-left">
          <h2 class="header-title">{{ pageTitle }}</h2>
        </div>
        <div class="header-section section-right">
          <div class="monitor-status" :class="{ 'is-active': schedulerStatus.is_running }">
            {{ schedulerStatus.is_running ? '监控运行中' : '监控已暂停' }}
          </div>
          <el-button
            :type="schedulerStatus.is_running ? 'danger' : 'success'"
            @click="toggleScheduler"
            :loading="toggleLoading"
            circle
            plain
            :icon="toggleLoading ? undefined : (schedulerStatus.is_running ? VideoPause : VideoPlay)"
          />
          <el-button
            type="primary"
            @click="handleGlobalRefresh"
            :loading="refreshLoading"
            circle
            plain
            :icon="refreshLoading ? undefined : Refresh"
          />
        </div>
      </el-header>

      <el-main class="app-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, provide } from 'vue'
import { useRoute } from 'vue-router'
import { VideoPause, VideoPlay, Refresh } from '@element-plus/icons-vue'
import { getSchedulerStatus, pauseScheduler, resumeScheduler, createEventSource } from '@/api'
import type { SSEEvent } from '@/api'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { logger } from '@/utils/logger'

const route = useRoute()

const isSidebarCollapsed = ref(false)
const toggleSidebar = () => { isSidebarCollapsed.value = !isSidebarCollapsed.value }

const pageTitle = computed(() => (route.meta?.title as string) || '监控仪表盘')

const schedulerStatus = ref({ is_running: false, is_paused: false })
const toggleLoading = ref(false)
const refreshLoading = ref(false)
let eventSource: EventSource | null = null

const refreshCallbacks = ref<Array<() => Promise<void>>>([])

const registerRefreshCallback = (callback: () => Promise<void>) => {
  refreshCallbacks.value.push(callback)
}

const unregisterRefreshCallback = (callback: () => Promise<void>) => {
  const index = refreshCallbacks.value.indexOf(callback)
  if (index > -1) refreshCallbacks.value.splice(index, 1)
}

const handleGlobalRefresh = async () => {
  refreshLoading.value = true
  try {
    await Promise.all(refreshCallbacks.value.map(cb => cb()))
  } finally {
    refreshLoading.value = false
  }
}

provide('registerRefreshCallback', registerRefreshCallback)
provide('unregisterRefreshCallback', unregisterRefreshCallback)

const fetchSchedulerStatus = async () => {
  try {
    schedulerStatus.value = await getSchedulerStatus()
  } catch (error) {
    logger.error('获取调度器状态失败', error, { sampling: 5000 })
  }
}

const toggleScheduler = async () => {
  toggleLoading.value = true
  try {
    if (schedulerStatus.value.is_running) await pauseScheduler()
    else await resumeScheduler()
    await fetchSchedulerStatus()
  } catch (error) {
    logger.error('切换调度器状态失败', error)
  } finally {
    toggleLoading.value = false
  }
}

const handleSSEEvent = (event: SSEEvent) => {
  if (event.type === 'connected') logger.debug('SSE已连接到事件流')
  else if (event.type === 'sync_complete' || event.type === 'monitor_complete') fetchSchedulerStatus()
}

onMounted(() => {
  fetchSchedulerStatus()
  eventSource = createEventSource(handleSSEEvent, () => {
    logger.info('SSE连接失败，5秒后重连', null, { sampling: 10000 })
    setTimeout(() => {
      if (eventSource) eventSource.close()
      eventSource = createEventSource(handleSSEEvent)
    }, 5000)
  })
})

onUnmounted(() => {
  if (eventSource) { eventSource.close(); eventSource = null }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

.app-layout { height: 100vh; display: flex; }

.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--bg-color);
}

.app-header {
  background-color: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color-lighter);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-xl);
  height: var(--header-height);
  z-index: 10;
}

.header-title { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--text-color-primary); }
.header-section { display: flex; align-items: center; }
.section-right { gap: var(--spacing-sm); }

.monitor-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--text-color-regular);
  padding: 6px 12px;
  background: var(--border-color-extra-light);
  border-radius: 20px;
  transition: all 0.3s ease;
}

.monitor-status.is-active { background: rgba(103, 194, 58, 0.1); color: var(--el-color-success); }

.app-content {
  padding: var(--spacing-lg) var(--spacing-xl);
  overflow-y: auto;
  height: calc(100vh - var(--header-height));
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.el-card__header {
  border-bottom: 1px solid var(--border-color-lighter);
  padding: 20px 24px;
  font-weight: 600;
  font-size: var(--font-size-md);
  color: var(--text-color-primary);
}

.el-table {
  --el-table-header-bg-color: var(--bg-color);
  --el-table-row-hover-bg-color: var(--el-color-primary-light-9);
}

.el-table th.el-table__cell { font-weight: 600; color: var(--text-color-primary); }
</style>
