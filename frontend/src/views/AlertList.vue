<template>
  <div class="page-wrapper">
    <div class="page-toolbar">
      <div class="page-toolbar__left">
        <el-autocomplete
          v-model="filters.symbol"
          :fetch-suggestions="querySymbols"
          placeholder="输入交易对名称"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
          @select="handleSearch"
          :trigger-on-focus="false"
          highlight-first-item
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #default="{ item }">
            <div class="symbol-suggestion">
              <span class="symbol-name">{{ item.value }}</span>
              <el-tag v-if="item.is_active" type="success" size="small">监控中</el-tag>
              <el-tag v-else type="info" size="small">未监控</el-tag>
            </div>
          </template>
        </el-autocomplete>
        
        <el-date-picker
          v-model="filters.timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DDTHH:mm:ss"
          :shortcuts="dateShortcuts"
          clearable
          class="time-range-picker"
          @change="handleSearch"
        />

        <el-select v-model="filters.alert_type" placeholder="全部类型" class="filter-select" clearable @change="handleSearch">
          <el-option label="全部类型" :value="undefined" />
          <el-option label="成交量提醒" :value="1" />
          <el-option label="涨幅提醒" :value="2" />
          <el-option label="开盘价匹配" :value="3" />
        </el-select>

        <div class="button-group">
          <el-button @click="handleReset">重置</el-button>
        </div>
      </div>

      <div class="page-toolbar__right">
        <el-button type="danger" plain @click="handleClearAll">
          清空提醒记录
        </el-button>
      </div>
    </div>

    <div class="page-content" v-loading="loading">
      <el-empty v-if="alerts.length === 0 && !loading" description="暂无提醒记录" />
      
      <div v-else class="card-grid">
          <div v-for="alert in alerts" :key="alert.id" class="card-grid__item">
            <AlertCard :alert="alert">
              <template #actions>
                <el-button type="info" link size="small" class="delete-btn" @click="handleDelete(alert.id)">
                  <el-icon :size="18"><Delete /></el-icon>
                </el-button>
              </template>
            </AlertCard>
          </div>
      </div>
    </div>

    <div class="page-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100, 500, 1000]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        background
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AlertCard from '@/components/alert/AlertCard.vue'
import { getAlerts, deleteAlert, deleteAllAlerts, getSymbols } from '@/api'
import type { Alert, Symbol } from '@/types'
import { Search, Delete, Refresh } from '@element-plus/icons-vue'

const loading = ref(false)
const alerts = ref<Alert[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const symbolsCache = ref<Symbol[]>([])

const filters = reactive({
  alert_type: undefined as number | undefined,
  symbol: '',
  timeRange: null as [string, string] | null
})

const dateShortcuts = [
  {
    text: '最近1小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000)
      return [start, end]
    }
  },
  {
    text: '今天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setHours(0, 0, 0, 0)
      return [start, end]
    }
  },
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    }
  }
]

// 加载交易对列表用于自动补全
const loadSymbols = async () => {
  try {
    const data = await getSymbols({ limit: 1000 })
    symbolsCache.value = data.items
  } catch (error) {
    console.error('加载交易对列表失败:', error)
  }
}

// 交易对自动补全查询
const querySymbols = (queryString: string, cb: (suggestions: any[]) => void) => {
  if (!queryString) {
    cb([])
    return
  }
  
  const query = queryString.toUpperCase()
  const results = symbolsCache.value
    .filter(s => s.symbol.includes(query))
    .slice(0, 20)
    .map(s => ({
      value: s.symbol,
      is_active: s.is_active
    }))
  
  cb(results)
}

const fetchData = async () => {
  loading.value = true
  try {
    const data = await getAlerts({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      alert_type: filters.alert_type,
      symbol: filters.symbol || undefined,
      start_time: filters.timeRange?.[0] || undefined,
      end_time: filters.timeRange?.[1] || undefined
    })
    alerts.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error('获取提醒列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => { currentPage.value = 1; fetchData() }
const handleReset = () => { filters.alert_type = undefined; filters.symbol = ''; filters.timeRange = null; currentPage.value = 1; fetchData() }
const handlePageChange = () => fetchData()
const handleSizeChange = () => { currentPage.value = 1; fetchData() }

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

const handleClearAll = () => {
  ElMessageBox.confirm(
    '确定要清空当前筛选条件下的所有记录吗?',
    '确认清空',
    {
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
      showClose: false
    }
  )
    .then(async () => {
      try {
        await deleteAllAlerts(filters.alert_type)
        ElMessage.success('清空成功')
        fetchData()
      } catch {
        ElMessage.error('清空失败')
      }
    })
    .catch(() => {})
}

onMounted(() => {
  loadSymbols()
  fetchData()
})
</script>

<style scoped>
.page-wrapper { 
  height: 100%; 
  display: flex; 
  flex-direction: column; 
  overflow: hidden; 
}

.page-toolbar { 
  flex-shrink: 0; 
  margin-bottom: var(--spacing-lg); 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
}

.page-toolbar__left { 
  display: flex; 
  gap: var(--spacing-md); 
  align-items: center; 
}

.button-group {
  display: flex;
  gap: var(--spacing-xs);
}

/* Inherited from theme.css but good to be explicit if scoped */
.search-input { width: 240px; }
.filter-select { width: 160px; }
.time-range-picker { width: 360px; }

.page-content { 
  flex: 1; 
  overflow-y: auto; 
  min-height: 0; 
  padding-right: 4px; 
}

.card-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
  gap: var(--spacing-lg); 
}

.page-footer { 
  flex-shrink: 0; 
  margin-top: var(--spacing-lg); 
  display: flex; 
  justify-content: flex-end; 
  padding-top: var(--spacing-sm); 
}

.symbol-suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: var(--spacing-sm);
}

.symbol-name {
  flex: 1;
  font-weight: 500;
}
</style>
