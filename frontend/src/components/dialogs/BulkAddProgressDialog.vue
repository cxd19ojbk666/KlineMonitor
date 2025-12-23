<template>
  <el-dialog
    v-model="visible"
    title="批量添加进度"
    width="520px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    class="sync-dialog bulk-add-dialog unified-dialog"
    align-center
    center
  >
    <div class="sync-content">
      <div class="sync-header">
        <div class="sync-icon-wrapper" :class="{ 'is-completed': complete }">
          <div class="loading-spinner" v-if="!complete">
            <div class="spinner-dot" v-for="i in 8" :key="i"></div>
          </div>
          <el-icon v-else size="28" color="#67c23a"><CircleCheckFilled /></el-icon>
        </div>
        <div class="sync-title-info">
          <h3>{{ complete ? '添加完成' : '正在添加' }}</h3>
          <p v-if="!complete && phase === 'syncing'">并发同步中，已完成 {{ current }} / {{ total }} 个任务</p>
          <p v-else-if="!complete">共 {{ total }} 个交易对</p>
          <p v-else>所有交易对添加完成</p>
        </div>
      </div>
      
      <div class="progress-wrapper">
        <el-progress
          :percentage="progress"
          :status="complete ? 'success' : ''"
          :stroke-width="10"
          :show-text="false"
          color="#409eff"
        />
        <span class="progress-text">{{ progress }}%</span>
      </div>
      
      <div class="sync-status-text">
        <template v-if="phase === 'syncing'">
          <span>已同步 {{ result.synced.toLocaleString() }} 条K线数据</span>
        </template>
        <template v-else-if="phase === 'adding'">
          <span>{{ current }} / {{ total }} - {{ currentSymbol }}</span>
        </template>
        <template v-else-if="complete">
          <span>新增 {{ result.added }} 个交易对，同步 {{ result.synced.toLocaleString() }} 条K线数据</span>
        </template>
        <template v-else>
          <span>{{ message }}</span>
        </template>
      </div>

      <!-- 完成后显示各周期统计 -->
      <div class="stats-summary" v-if="complete && result.stats && result.stats.length > 0">
        <div class="stats-title">各周期同步统计：</div>
        <div class="stats-list">
          <span v-for="(stat, idx) in result.stats" :key="idx" class="stat-item">{{ stat }}</span>
        </div>
      </div>

      <div class="bulk-add-log" v-if="logs.length > 0">
        <div
          v-for="(log, idx) in logs"
          :key="idx"
          class="log-tag"
          :class="log.status"
        >
          <span class="log-symbol">{{ log.symbol }}</span>
          <span class="log-status-icon">
            <el-icon v-if="log.status === 'done'"><Check /></el-icon>
            <el-icon v-else-if="log.status === 'syncing'" class="is-loading"><Loading /></el-icon>
            <el-icon v-else-if="log.status === 'partial'"><Warning /></el-icon>
            <el-icon v-else-if="log.status === 'error'"><Close /></el-icon>
          </span>
        </div>
      </div>
    </div>
    
    <template #footer v-if="complete">
      <el-button type="primary" @click="handleClose" style="width: 100%">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { CircleCheckFilled, Check, Loading, Warning, Close } from '@element-plus/icons-vue'
import type { BulkAddLog } from '@/composables/useBulkAdd'

const visible = defineModel<boolean>({ default: false })

defineProps<{
  complete: boolean
  progress: number
  message: string
  phase: string
  total: number
  current: number
  currentSymbol: string
  result: { added: number; synced: number; failed: number; stats?: string[] }
  logs: BulkAddLog[]
}>()

const emit = defineEmits<{
  close: []
}>()

const handleClose = () => {
  visible.value = false
  emit('close')
}
</script>

<style>
@import '@/styles/dialog.css';

.stats-summary {
  margin-top: 16px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.stats-title {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.stats-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stat-item {
  font-size: 12px;
  color: var(--el-text-color-regular);
  background: var(--el-bg-color);
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
