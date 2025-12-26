<template>
  <div class="page-wrapper">
    <!-- 交易对列表 -->
    <div class="page-toolbar">
      <div class="page-toolbar__left">
        <el-input v-model="searchText" placeholder="输入交易对名称" clearable class="search-input" @keyup.enter="handleSearch" @clear="handleSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterActive" placeholder="状态筛选" class="filter-select--small" clearable @change="handleSearch" @clear="handleSearch">
          <el-option label="全部状态" :value="undefined" />
          <el-option label="已启用" :value="true" />
          <el-option label="未启用" :value="false" />
        </el-select>
      </div>
      <div class="page-toolbar__right">
        <div class="page-toolbar__actions">
          <span class="selection-info" v-if="hasSelection">
            已选 <span class="selection-info__count">{{ selectedCount }}</span> 个
          </span>
          <el-button type="success" plain :disabled="selectionDisabled" @click="handleBatchActivate(true)">
            批量启用
          </el-button>
          <el-button type="warning" plain :disabled="selectionDisabled" @click="handleBatchActivate(false)">
            批量停用
          </el-button>
          <el-button type="danger" plain :disabled="selectionDisabled" @click="handleBatchDelete">
            批量删除
          </el-button>
          <el-button type="primary" @click="showAddDialog = true">
            添加
          </el-button>
          <el-button type="success" @click="bulkAdd.fetchAvailableSymbols()">
            一键添加
          </el-button>
        </div>
      </div>
    </div>

    <div class="page-content">
      <el-table :data="symbols" v-loading="loading" stripe row-key="symbol" style="width: 100%" class="symbol-table" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" align="center" />
        <el-table-column prop="symbol" label="交易对">
          <template #default="{ row }">
            <div class="symbol-cell">
              <div class="symbol-icon">{{ row.symbol[0] }}</div>
              <span class="symbol-text">{{ row.symbol }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain" round>
              {{ row.is_active ? '监控中' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="添加时间">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="right">
          <template #default="{ row }">
            <el-button :type="row.is_active ? 'warning' : 'success'" text bg size="small" @click="handleToggle(row.symbol)">
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button type="danger" text bg size="small" @click="handleDelete(row.symbol)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
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
    
    <!-- 手动添加弹窗 -->
    <AddSymbolDialog v-model="showAddDialog" :loading="addLoading" @confirm="handleAdd" />

    <!-- 一键添加确认弹窗 -->
    <BulkAddConfirmDialog
      v-model="bulkAdd.showConfirmDialog.value"
      :available-info="bulkAdd.availableInfo.value"
      :loading="bulkAdd.loading.value"
      @confirm="() => bulkAdd.startBulkAdd(fetchData)"
    />

    <!-- 批量添加进度弹窗 -->
    <BulkAddProgressDialog
      v-model="bulkAdd.showProgressDialog.value"
      :complete="bulkAdd.complete.value"
      :progress="bulkAdd.progress.value"
      :message="bulkAdd.message.value"
      :phase="bulkAdd.phase.value"
      :total="bulkAdd.total.value"
      :current="bulkAdd.current.value"
      :current-symbol="bulkAdd.currentSymbol.value"
      :result="bulkAdd.result"
      :logs="bulkAdd.logs.value"
      @close="fetchData"
    />

    <!-- 数据同步进度弹窗 -->
    <SyncProgressDialog
      v-model="sync.showSyncDialog.value"
      :symbol="sync.syncingSymbol.value"
      :progress="sync.syncProgress.value"
      :complete="sync.syncComplete.value"
      :current-interval="sync.currentInterval.value"
      :details="sync.syncDetails.value"
    />

    <!-- 删除确认弹窗 -->
    <!-- Removed ConfirmDialog -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Search, Plus, Close, Delete, FolderAdd } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getSymbols, createSymbol, toggleSymbol, deleteSymbol, batchActivateSymbols, batchDeleteSymbols } from '@/api'
import type { Symbol } from '@/types'
import { useSymbolSync } from '@/composables/useSymbolSync'
import { useBulkAdd } from '@/composables/useBulkAdd'
import AddSymbolDialog from '@/components/dialogs/AddSymbolDialog.vue'
import BulkAddConfirmDialog from '@/components/dialogs/BulkAddConfirmDialog.vue'
import BulkAddProgressDialog from '@/components/dialogs/BulkAddProgressDialog.vue'
import SyncProgressDialog from '@/components/dialogs/SyncProgressDialog.vue'

const loading = ref(false)
const addLoading = ref(false)
const symbols = ref<Symbol[]>([])
const selectedSymbols = ref<Symbol[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchText = ref('')
const filterActive = ref<boolean | undefined>(undefined)
const showAddDialog = ref(false)

// 使用 composables
const sync = useSymbolSync()
const bulkAdd = useBulkAdd()

const selectedCount = computed(() => selectedSymbols.value.length)
const hasSelection = computed(() => selectedCount.value > 0)
const selectedSymbolNames = computed(() => selectedSymbols.value.map(s => s.symbol))
const selectionDisabled = computed(() => !hasSelection.value || loading.value)

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm')

const fetchData = async () => {
  loading.value = true
  try {
    const data = await getSymbols({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      is_active: filterActive.value,
      symbol: searchText.value || undefined
    })
    symbols.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error('获取交易对列表失败')
  } finally {
    loading.value = false
    selectedSymbols.value = []
  }
}

const handleSearch = () => { currentPage.value = 1; fetchData() }
const handlePageChange = () => fetchData()
const handleSizeChange = () => { currentPage.value = 1; fetchData() }

const handleAdd = async (symbol: string) => {
  addLoading.value = true
  try {
    await createSymbol(symbol)
    showAddDialog.value = false
    sync.startSync(symbol.toUpperCase())
    fetchData()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '添加失败')
  } finally {
    addLoading.value = false
  }
}

const handleToggle = async (symbol: string) => {
  try {
    await toggleSymbol(symbol)
    fetchData()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleDelete = (symbol: string) => {
  ElMessageBox.confirm(
    '确定删除该交易对吗? 删除后将清除相关数据。',
    '确认删除',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      showClose: false
    }
  )
    .then(async () => {
      try {
        await deleteSymbol(symbol)
        ElMessage.success('删除成功')
        fetchData()
      } catch (error: any) {
        ElMessage.error(error?.response?.data?.detail || '删除失败')
      }
    })
    .catch(() => {})
}

const handleSelectionChange = (selection: Symbol[]) => {
  selectedSymbols.value = selection
}

const ensureSelection = () => {
  if (!selectedSymbolNames.value.length) {
    ElMessage.warning('请选择需要操作的交易对')
    return false
  }
  return true
}

const handleBatchActivate = async (is_active: boolean) => {
  if (!ensureSelection()) return
  try {
    await batchActivateSymbols(selectedSymbolNames.value, is_active)
    ElMessage.success(is_active ? '批量启用成功' : '批量停用成功')
    fetchData()
  } catch {
    ElMessage.error('批量操作失败')
  }
}

const handleBatchDelete = () => {
  if (!ensureSelection()) return
  
  ElMessageBox.confirm(
    '确定删除选中的交易对吗？删除后将清除所有相关K线数据。',
    '确认批量删除',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      showClose: false
    }
  )
    .then(async () => {
      try {
        await batchDeleteSymbols(selectedSymbolNames.value)
        ElMessage.success('批量删除成功')
        fetchData()
      } catch (error: any) {
        ElMessage.error(error?.response?.data?.detail || '批量删除失败')
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

.page-content { 
  flex: 1; 
  overflow-y: auto; 
  min-height: 0; 
  padding-right: 4px; 
}

.page-footer { 
  flex-shrink: 0; 
  margin-top: var(--spacing-lg); 
  display: flex; 
  justify-content: flex-end; 
  align-items: center; 
  padding-top: var(--spacing-sm); 
}

.page-toolbar { 
  display: flex; 
  justify-content: space-between; 
  align-items: flex-start; 
  flex-wrap: wrap; 
  gap: var(--spacing-md); 
  margin-bottom: var(--spacing-lg);
}

.page-toolbar__left { 
  display: flex; 
  gap: var(--spacing-md); 
  flex-wrap: wrap; 
  align-items: center;
}

.page-toolbar__right { 
  display: flex; 
  align-items: center; 
  gap: var(--spacing-sm); 
}

.page-toolbar__actions { 
  display: flex; 
  gap: var(--spacing-xs); 
  flex-wrap: wrap; 
  justify-content: flex-end; 
}

.selection-info { 
  font-size: var(--font-size-sm); 
  color: var(--text-color-regular); 
  display: flex; 
  align-items: center; 
  margin-right: var(--spacing-sm);
}

.selection-info__count { 
  color: var(--el-color-primary); 
  font-weight: var(--font-weight-semibold); 
  margin: 0 4px; 
}

.symbol-table { 
  --el-table-header-bg-color: var(--bg-color-overlay); 
  --el-table-tr-bg-color: var(--bg-color-overlay); 
}

.symbol-cell { 
  display: flex; 
  align-items: center; 
  gap: var(--spacing-sm); 
}

.symbol-icon { 
  width: 32px; 
  height: 32px; 
  background: var(--border-color-extra-light); 
  border-radius: 50%; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  font-weight: var(--font-weight-bold); 
  color: var(--el-color-primary); 
  font-size: var(--font-size-md); 
}

.symbol-text { 
  font-weight: var(--font-weight-semibold); 
  color: var(--text-color-primary); 
}
</style>
