<template>
  <div class="sidebar-container" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-header">
      <div class="icon-column" @click="toggleCollapse">
        <el-icon class="toggle-icon"><Expand v-if="isCollapsed" /><Fold v-else /></el-icon>
      </div>
      <div class="header-text">
        <span>K线监控系统</span>
      </div>
    </div>

    <div class="sidebar-menu">
      <div
        v-for="item in menuItems"
        :key="item.index"
        class="menu-item"
        :class="{ active: currentRoute === item.index }"
        @click="handleSelect(item.index)"
      >
        <div class="icon-column">
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
        </div>
        <div class="text-content">
          <span>{{ item.title }}</span>
        </div>
      </div>

      <div class="menu-spacer"></div>

      <div
        class="menu-item"
        :class="{ active: currentRoute === '/settings' }"
        @click="handleSelect('/settings')"
      >
        <div class="icon-column">
          <el-icon :size="20"><Setting /></el-icon>
        </div>
        <div class="text-content">
          <span>参数设置</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Monitor, DataLine, Bell, Coin, Setting, Expand, Fold, Document } from '@element-plus/icons-vue'

const props = defineProps<{ isCollapsed: boolean }>()
const emit = defineEmits<{ (e: 'toggle-collapse'): void }>()

const route = useRoute()
const router = useRouter()
const currentRoute = computed(() => route.path)

const menuItems = [
  { index: '/', title: '监控仪表盘', icon: Monitor },
  { index: '/monitor', title: '交易对监控', icon: DataLine },
  { index: '/alerts', title: '提醒记录', icon: Bell },
  { index: '/symbols', title: '交易对管理', icon: Coin },
  { index: '/logs', title: '日志查看', icon: Document },
]

const handleSelect = (index: string) => router.push(index)
const toggleCollapse = () => emit('toggle-collapse')
</script>

<style scoped>
.sidebar-container {
  height: 100vh;
  background-color: var(--bg-color-overlay);
  color: var(--text-color-primary);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.25, 0.8, 0.5, 1);
  width: var(--sidebar-width);
  overflow: hidden;
  border-right: 1px solid var(--border-color-light);
  font-family: 'Inter', sans-serif;
}

.sidebar-container.collapsed { width: var(--sidebar-collapsed-width); }

.sidebar-header { 
  height: 80px; 
  display: flex; 
  align-items: center; 
  margin-bottom: var(--spacing-md);
}

.icon-column {
  width: var(--sidebar-collapsed-width);
  min-width: var(--sidebar-collapsed-width);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.toggle-icon { font-size: 24px; color: var(--text-color-primary); }

.header-text {
  flex: 1;
  white-space: nowrap;
  opacity: 1;
  transition: opacity 0.2s ease;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-color-primary);
  letter-spacing: 1px;
}

.sidebar-container.collapsed .header-text { opacity: 0; pointer-events: none; }

.sidebar-menu { 
  flex: 1; 
  display: flex; 
  flex-direction: column; 
  padding: 0 var(--spacing-md) var(--spacing-lg) var(--spacing-md); 
  gap: var(--spacing-sm); 
}

.menu-item {
  height: 56px;
  display: flex;
  align-items: center;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  color: var(--text-color-regular);
}

.menu-item:hover { 
  background-color: rgba(0, 0, 0, 0.05); 
  color: var(--text-color-primary); 
}

.menu-item.active { 
  background-color: var(--el-color-primary-light-9); 
  color: var(--el-color-primary); 
}

.menu-item .icon-column { 
  width: 48px; 
  min-width: 48px; 
  height: 48px; 
}

.text-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 1;
  transition: opacity 0.2s ease, transform 0.2s ease;
  padding-right: var(--spacing-sm);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
}

.sidebar-container.collapsed .text-content { opacity: 0; transform: translateX(10px); pointer-events: none; }
.menu-spacer { margin-top: auto; }
</style>
