<template>
  <el-dialog
    v-model="visible"
    title="批量添加交易对"
    width="480px"
    destroy-on-close
    class="add-symbol-dialog unified-dialog"
    center
    align-center
    :show-close="false"
  >
    <div class="add-dialog-content">
      <div class="dialog-icon-wrapper">
        <el-icon :size="40" color="var(--el-color-primary)"><FolderAdd /></el-icon>
      </div>
      <p class="dialog-instruction">即将添加所有 Binance USDT 永续合约交易对</p>
      
      <div class="bulk-add-stats-wrapper animate-up" v-if="availableInfo">
        <div class="stat-item">
          <span class="stat-value">{{ availableInfo.total_binance }}</span>
          <span class="stat-label">总交易对</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ availableInfo.existing }}</span>
          <span class="stat-label">已添加</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item highlight">
          <span class="stat-value">{{ availableInfo.available }}</span>
          <span class="stat-label">本次添加</span>
        </div>
      </div>
      
      <div v-else class="loading-info">
        <div class="loading-spinner">
          <div class="spinner-dot" v-for="i in 8" :key="i"></div>
        </div>
        <span>正在获取交易对数据...</span>
      </div>
      
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel" size="large" class="dialog-btn">取消</el-button>
        <el-button
          type="primary"
          @click="handleConfirm"
          :disabled="!availableInfo || availableInfo.available === 0"
          :loading="loading"
          size="large"
          class="dialog-btn submit-btn"
        >
          开始添加
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { FolderAdd } from '@element-plus/icons-vue'
import type { AvailableSymbolsResponse } from '@/types'

const visible = defineModel<boolean>({ default: false })

defineProps<{
  availableInfo: AvailableSymbolsResponse | null
  loading?: boolean
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  visible.value = false
  emit('cancel')
}
</script>

<style>
@import '@/styles/dialog.css';
</style>

<style scoped>
.add-dialog-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
}

.dialog-icon-wrapper {
  margin-bottom: 20px;
  background: var(--el-color-primary-light-9);
  width: 88px;
  height: 88px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.dialog-instruction {
  font-size: var(--font-size-md);
  color: var(--text-color-primary);
  margin: 0 0 28px 0;
  font-weight: var(--font-weight-medium);
  text-align: center;
}

.bulk-add-stats-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-evenly;
  background: transparent;
  border: 1px solid var(--border-color-lighter);
  border-radius: var(--radius-lg);
  padding: 24px 16px;
  margin-bottom: 16px;
  width: 100%;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
}

.bulk-add-stats-wrapper:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--el-color-primary-light-7);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--border-color-light);
  transform: scaleX(0.5);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.stat-item .stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-color-secondary);
  font-weight: var(--font-weight-regular);
}

.stat-item .stat-value {
  font-size: 28px;
  line-height: 1.2;
  font-weight: var(--font-weight-semibold);
  color: var(--text-color-primary);
  font-family: var(--font-family-monospace);
  letter-spacing: -0.5px;
}

.stat-item.highlight .stat-value {
  color: var(--el-color-primary);
}

.loading-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 32px 0;
  color: var(--text-color-secondary);
  background: var(--bg-color);
  width: 100%;
  border-radius: var(--radius-lg);
  border: 1px dashed var(--border-color-lighter);
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: center;
  gap: 16px;
}

.dialog-btn {
  min-width: 120px;
  font-weight: var(--font-weight-medium);
}
</style>
