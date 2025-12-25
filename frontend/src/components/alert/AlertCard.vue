<template>
  <div class="alert-card-wrapper" :class="[`type-${alert.alert_type}`]">
    <div class="alert-card-content">
      <!-- 头部：交易对 + 类型标签 -->
      <div class="card-header">
        <div class="header-left">
          <div class="symbol-row">
            <span class="symbol-name">{{ alert.symbol }}</span>
            <span class="time-text">{{ formattedTime }}</span>
          </div>
          <div class="tags-row">
            <span class="type-badge">{{ typeName }}</span>
            <span class="interval-badge" v-if="alert.alert_type === 3">{{ (data as OpenPriceAlertData).timeframe }}</span>
          </div>
        </div>
      </div>

      <!-- 分隔线 -->
      <div class="divider"></div>

      <!-- 内容区域 -->
      <div class="card-body">
        <!-- 类型1：成交量提醒 -->
        <template v-if="alert.alert_type === 1">
          <div class="data-grid">
            <div class="data-item">
              <span class="label">15分钟Vol</span>
              <span class="value">{{ formatVolume(data.volume_15m) }}</span>
            </div>
            <div class="data-item">
              <span class="label">8小时Vol</span>
              <span class="value">{{ formatVolume(data.volume_8h) }}</span>
            </div>
            <div class="data-item">
              <span class="label">Vol占比</span>
              <span class="value highlight">{{ data.volume_ratio?.toFixed(1) }}%</span>
            </div>
          </div>
        </template>

        <!-- 类型2：涨幅提醒 -->
        <template v-else-if="alert.alert_type === 2">
          <div class="data-grid">
            <div class="data-item">
              <span class="label">最近Close</span>
              <span class="value">{{ formatPrice(data.rise_end_price) }}</span>
            </div>
            <div class="data-item">
              <span class="label">15m前Open</span>
              <span class="value text-secondary">{{ formatPrice(data.rise_start_price) }}</span>
            </div>
            <div class="data-item">
              <span class="label">涨幅</span>
              <span class="value" :class="getPnlClass(data.rise_percent)">
                {{ data.rise_percent >= 0 ? '+' : '' }}{{ data.rise_percent?.toFixed(2) }}%
              </span>
            </div>
          </div>
        </template>

        <!-- 类型3：开盘价匹配 -->
        <template v-else-if="alert.alert_type === 3">
          <div class="data-grid">
            <div class="data-item">
              <span class="label">当前Open</span>
              <span class="value">{{ formatPrice(data.price_d) }}</span>
            </div>
            <div class="data-item">
              <span class="label">匹配Open</span>
              <span class="value">{{ formatPrice(data.price_e) }}</span>
            </div>
            <div class="data-item">
              <span class="label">价格误差</span>
              <span class="value">{{ data.price_error?.toFixed(2) }}%</span>
            </div>
            <div class="data-item">
              <span class="label">匹配时间</span>
              <span class="value">{{ formatTime(data.time_e) }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- 底部操作 -->
      <div class="card-action-overlay" v-if="$slots.actions">
        <slot name="actions"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import dayjs from 'dayjs'
import type { Alert, VolumeAlertData, RiseAlertData, OpenPriceAlertData } from '@/types'

const props = defineProps<{ alert: Alert }>()

const formattedTime = computed(() => dayjs(props.alert.created_at).format('MM-DD HH:mm'))

const typeName = computed(() => {
  const names: Record<number, string> = { 1: '成交量', 2: '涨幅', 3: '开盘价匹配' }
  return names[props.alert.alert_type] || '提醒'
})

const data = computed(() => props.alert.data as VolumeAlertData | RiseAlertData | OpenPriceAlertData)

const formatPrice = (price?: number): string => {
  if (!price) return '-'
  if (price >= 1000) return price.toFixed(2)
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}

const formatVolume = (volume?: number): string => {
  if (!volume) return '-'
  return volume.toLocaleString('en-US', { maximumFractionDigits: 0 })
}

const getPnlClass = (percent: number) => {
  return percent > 0 ? 'text-success' : 'text-danger'
}

const formatTime = (time?: string): string => {
  if (!time) return '-'
  return dayjs(time).format('MM-DD HH:mm')
}
</script>

<style scoped>
.alert-card-wrapper {
  position: relative;
  height: 190px;
  background: var(--bg-color-overlay);
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--border-color-lighter);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}


.alert-card-content {
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
  z-index: 1;
}

/* 头部样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-sm);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.symbol-row {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
}

.symbol-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--text-color-primary);
  line-height: 1.2;
}

.time-text {
  font-size: var(--font-size-xs);
  color: var(--text-color-placeholder);
  font-family: var(--font-family-monospace);
}

.tags-row {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
}

.type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
}

.type-1 .type-badge { color: #409EFF; background: rgba(64, 158, 255, 0.1); }
.type-2 .type-badge { color: #F56C6C; background: rgba(245, 108, 108, 0.1); }
.type-3 .type-badge { color: #E6A23C; background: rgba(230, 162, 60, 0.1); }

.interval-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-color-page);
  color: var(--text-color-secondary);
  border: 1px solid var(--border-color-lighter);
}

.divider {
  height: 1px;
  background: var(--border-color-extra-light);
  margin: 0 calc(var(--spacing-md) * -1) var(--spacing-sm);
  width: calc(100% + var(--spacing-xl));
}

/* 内容区域 */
.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.data-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
}

.data-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.data-item .label {
  font-size: 11px;
  color: var(--text-color-secondary);
  letter-spacing: 0.5px;
}

.data-item .value {
  font-size: 15px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-color-primary);
  font-family: var(--font-family-monospace);
}

.value.text-secondary { color: var(--text-color-regular); }

.text-success { color: var(--el-color-success); }
.text-danger { color: var(--el-color-danger); }

/* 悬浮操作层 */
.card-action-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transform: scale(0.9);
  transition: all 0.2s;
  background: var(--bg-color-overlay);
  border-radius: var(--radius-md);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 4px;
}

.alert-card-wrapper:hover .card-action-overlay {
  opacity: 1;
  transform: scale(1);
}
</style>