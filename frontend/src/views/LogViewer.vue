<template>
  <div class="page-wrapper">
    <div class="page-content">
      <el-card class="log-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <el-radio-group v-model="logType" @change="handleLogTypeChange">
                <el-radio-button value="app">全部</el-radio-button>
                <el-radio-button value="info">INFO</el-radio-button>
                <el-radio-button value="warning">WARNING</el-radio-button>
                <el-radio-button value="error">ERROR</el-radio-button>
              </el-radio-group>
            </div>
            <div class="header-right">
              <el-input
                v-model="searchKeyword"
                placeholder="输入关键词搜索"
                clearable
                style="width: 200px;"
                @keyup.enter="loadLogContent"
                @clear="loadLogContent"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-input-number
                v-model="tailLines"
                :min="100"
                :max="5000"
                :step="100"
                controls-position="right"
                style="width: 120px; margin-left: 12px;"
              />
              <el-button type="primary" @click="loadLogContent" :loading="loading" style="margin-left: 12px;">
                刷新
              </el-button>
            </div>
          </div>
        </template>

        <div class="log-info" v-if="logContent">
          <span class="info-item">
            <el-icon><Document /></el-icon>
            {{ logContent.file_name }}
          </span>
          <span class="info-item">
            <el-icon><List /></el-icon>
            共 {{ logContent.total_lines }} 行
          </span>
          <span class="info-item">
            显示最后 {{ logContent.lines.length }} 行
          </span>
          <el-tag v-if="logContent.has_more" type="warning" size="small">部分显示</el-tag>
        </div>

        <div class="log-container" ref="logContainerRef">
          <div v-if="loading" class="log-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <div v-else-if="!logContent || logContent.lines.length === 0" class="log-empty">
            <el-empty description="暂无日志数据" />
          </div>
          <div v-else class="log-content">
            <div
              v-for="(line, index) in logContent.lines"
              :key="index"
              class="log-line"
              :class="getLineClass(line)"
            >
              <span class="line-number">{{ logContent.total_lines - logContent.lines.length + index + 1 }}</span>
              <span class="line-text" v-html="highlightSearch(line)"></span>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search, RefreshRight, Document, List, Loading } from '@element-plus/icons-vue'
import { getLogContent, type LogContent } from '@/api'
import { ElMessage } from 'element-plus'

const logType = ref<'app' | 'info' | 'warning' | 'error'>('app')
const selectedFile = ref('app.log')
const searchKeyword = ref('')
const tailLines = ref(500)
const loading = ref(false)
const logContent = ref<LogContent | null>(null)
const logContainerRef = ref<HTMLElement | null>(null)

const getLineClass = (line: string) => {
  if (line.includes(' - ERROR - ') || line.includes('[ERROR]')) return 'log-error'
  if (line.includes(' - WARNING - ') || line.includes('[WARNING]')) return 'log-warning'
  if (line.includes(' - DEBUG - ') || line.includes('[DEBUG]')) return 'log-debug'
  return ''
}

const highlightSearch = (line: string) => {
  if (!searchKeyword.value) return escapeHtml(line)
  const escaped = escapeHtml(line)
  const keyword = escapeHtml(searchKeyword.value)
  const regex = new RegExp(`(${keyword})`, 'gi')
  return escaped.replace(regex, '<mark class="search-highlight">$1</mark>')
}

const escapeHtml = (str: string) => {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const loadInitialLogs = async () => {
  await loadLogContent()
}

const loadLogContent = async () => {
  if (!selectedFile.value) return
  
  loading.value = true
  try {
    logContent.value = await getLogContent(selectedFile.value, {
      tail: tailLines.value,
      search: searchKeyword.value || undefined
    })
    // 滚动到底部
    setTimeout(() => {
      if (logContainerRef.value) {
        logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
      }
    }, 50)
  } catch (error) {
    ElMessage.error('加载日志内容失败')
  } finally {
    loading.value = false
  }
}

const handleLogTypeChange = () => {
  selectedFile.value = `${logType.value}.log`
  loadLogContent()
}

onMounted(() => {
  loadInitialLogs()
})
</script>

<style scoped>
.page-wrapper {
  height: calc(100vh - var(--header-height) - var(--spacing-lg) * 2);
  display: flex;
  flex-direction: column;
}

.page-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.log-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
}

.log-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--spacing-md);
  min-height: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.header-left, .header-right {
  display: flex;
  align-items: center;
}

.log-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--bg-color);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--text-color-secondary);
}

.info-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.log-container {
  flex: 1;
  background: #1e1e1e;
  border-radius: var(--radius-md);
  overflow: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-loading, .log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
  gap: var(--spacing-sm);
}

.log-loading .el-icon {
  font-size: 24px;
}

.log-content {
  padding: var(--spacing-sm);
}

.log-line {
  display: flex;
  padding: 2px 8px;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.line-number {
  flex-shrink: 0;
  min-width: 70px;
  color: #858585;
  text-align: right;
  padding-right: 12px;
  user-select: none;
  border-right: 1px solid #333;
  margin-right: 12px;
  white-space: nowrap;
}

.line-text {
  flex: 1;
}

.log-error {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
}

.log-warning {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}

.log-debug {
  color: #888;
}

:deep(.search-highlight) {
  background: #ffeb3b;
  color: #000;
  padding: 0 2px;
  border-radius: 2px;
}

:deep(.el-empty) {
  --el-empty-description-margin-top: 12px;
}

:deep(.el-empty__description p) {
  color: #888;
}
</style>
