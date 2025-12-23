<template>
  <el-dialog
    v-model="visible"
    title="数据同步进度"
    width="480px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    class="sync-dialog unified-dialog"
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
          <h3>{{ complete ? '同步完成' : '正在同步数据' }}</h3>
          <p>{{ symbol }}</p>
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
        <template v-if="!complete">
          <span>正在获取 {{ currentInterval }} 周期数据...</span>
        </template>
        <template v-else>
          <span>所有周期数据同步完毕</span>
        </template>
      </div>
      
      <div class="sync-details">
        <div v-for="item in details" :key="item.interval" class="sync-tag" :class="item.status">
          <span class="interval-text">{{ item.interval }}</span>
          <span class="status-icon">
            <el-icon v-if="item.status === 'done'"><Check /></el-icon>
            <el-icon v-else-if="item.status === 'syncing'" class="is-loading"><Loading /></el-icon>
            <el-icon v-else-if="item.status === 'error'"><Close /></el-icon>
            <el-icon v-else><MoreFilled /></el-icon>
          </span>
        </div>
      </div>
    </div>
    
    <template #footer v-if="complete">
      <el-button type="primary" @click="handleClose" style="width: 100%" size="large">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { CircleCheckFilled, Check, Loading, Close, MoreFilled } from '@element-plus/icons-vue'
import type { SyncDetail } from '@/composables/useSymbolSync'

const visible = defineModel<boolean>({ default: false })

defineProps<{
  symbol: string
  progress: number
  complete: boolean
  currentInterval: string
  details: SyncDetail[]
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
</style>
