<template>
  <el-card class="stat-card" shadow="hover">
    <div class="stat-content">
      <div class="stat-info">
        <div class="stat-title">{{ title }}</div>
        <div class="stat-value" :style="{ color: color || 'var(--el-color-primary)' }">{{ value }}</div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  value: number | string
  color?: string
}>()
</script>

<style scoped>
.stat-card {
  height: 100%;
  border: 1px solid var(--border-color-lighter);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-content {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: var(--spacing-sm);
}

.stat-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.stat-title {
  font-size: var(--font-size-sm);
  color: var(--text-color-regular);
  font-weight: var(--font-weight-medium);
}

.stat-value {
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  font-family: 'DIN Alternate', 'Roboto', sans-serif;
}
</style>
