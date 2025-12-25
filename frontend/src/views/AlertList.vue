<template>
  <div class="page-wrapper">
    <div class="page-toolbar">
      <div class="page-toolbar__left">
        <el-input
          v-model="filters.symbol"
          placeholder="输入交易对名称"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-select v-model="filters.alert_type" placeholder="全部类型" class="filter-select" clearable @change="handleSearch">
          <el-option label="全部类型" :value="undefined" />
          <el-option label="成交量提醒" :value="1" />
          <el-option label="涨幅提醒" :value="2" />
          <el-option label="开盘价匹配" :value="3" />
        </el-select>

        <div class="button-group">
          <el-button type="primary" @click="handleSearch">搜索</el-button>
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
import { getAlerts, deleteAlert, deleteAllAlerts } from '@/api'
import type { Alert } from '@/types'
import { Search, Delete, Refresh } from '@element-plus/icons-vue'

const loading = ref(false)
const alerts = ref<Alert[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const filters = reactive({
  alert_type: undefined as number | undefined,
  symbol: ''
})

const fetchData = async () => {
  loading.value = true
  try {
    const data = await getAlerts({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      alert_type: filters.alert_type,
      symbol: filters.symbol || undefined
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
const handleReset = () => { filters.alert_type = undefined; filters.symbol = ''; currentPage.value = 1; fetchData() }
const handlePageChange = () => fetchData()
const handleSizeChange = () => { currentPage.value = 1; fetchData() }

const handleDelete = (id: number) => {
  ElMessageBox.confirm(
    '确定要删除这条记录吗?',
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
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
      type: 'danger',
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

onMounted(() => fetchData())
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

.page-content { 
  flex: 1; 
  overflow-y: auto; 
  min-height: 0; 
  padding-right: 4px; 
}

.card-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
  gap: var(--spacing-lg); 
}

.page-footer { 
  flex-shrink: 0; 
  margin-top: var(--spacing-lg); 
  display: flex; 
  justify-content: flex-end; 
  padding-top: var(--spacing-sm); 
}
</style>
