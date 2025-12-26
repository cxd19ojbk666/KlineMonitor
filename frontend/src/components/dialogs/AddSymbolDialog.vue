<template>
  <el-dialog
    v-model="visible"
    title="新增交易对"
    width="420px"
    destroy-on-close
    class="add-symbol-dialog unified-dialog"
    center
    align-center
    :show-close="false"
  >
    <div class="add-dialog-content">
      <p class="dialog-instruction">请输入 Binance 交易对</p>
      <el-form :model="form" @submit.prevent="handleSubmit" size="large" style="width: 100%">
        <el-form-item style="margin-bottom: 16px">
          <el-autocomplete
            v-model="form.symbol"
            :fetch-suggestions="querySymbols"
            placeholder="例如：BTCUSDT"
            @keyup.enter="handleSubmit"
            @select="handleSelect"
            class="symbol-input"
            :trigger-on-focus="false"
            highlight-first-item
            style="width: 100%"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #default="{ item }">
              <div class="symbol-suggestion-item">
                <span class="symbol-name">{{ item.value }}</span>
                <el-tag v-if="item.exists" type="info" size="small">已添加</el-tag>
              </div>
            </template>
          </el-autocomplete>
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel" size="large">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="loading" size="large" class="submit-btn">
          确认
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getAvailableSymbols, getSymbols } from '@/api'

const visible = defineModel<boolean>({ default: false })

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  confirm: [symbol: string]
  cancel: []
}>()

const form = reactive({ symbol: '' })
const availableSymbols = ref<string[]>([])
const existingSymbols = ref<Set<string>>(new Set())

// 加载可用的交易对列表
const loadAvailableSymbols = async () => {
  try {
    const [available, existing] = await Promise.all([
      getAvailableSymbols(),
      getSymbols({ limit: 1000 })
    ])
    availableSymbols.value = available.symbols
    existingSymbols.value = new Set(existing.items.map(s => s.symbol))
  } catch (error) {
    console.error('加载交易对列表失败:', error)
  }
}

// 自动补全查询
const querySymbols = (queryString: string, cb: (suggestions: any[]) => void) => {
  if (!queryString) {
    cb([])
    return
  }
  
  const query = queryString.toUpperCase()
  const results = availableSymbols.value
    .filter(s => s.includes(query))
    .slice(0, 20)
    .map(s => ({
      value: s,
      exists: existingSymbols.value.has(s)
    }))
  
  cb(results)
}

const handleSelect = (item: { value: string }) => {
  form.symbol = item.value
}

watch(visible, (val) => {
  if (val) {
    form.symbol = ''
    if (availableSymbols.value.length === 0) {
      loadAvailableSymbols()
    }
  }
})

const handleSubmit = () => {
  if (form.symbol.trim()) {
    emit('confirm', form.symbol.trim().toUpperCase())
  }
}

const handleCancel = () => {
  visible.value = false
  emit('cancel')
}

onMounted(() => {
  loadAvailableSymbols()
})
</script>

<style>
@import '@/styles/dialog.css';
</style>

<style scoped>
.add-dialog-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.symbol-input :deep(.el-input__wrapper) {
  padding: 8px 15px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  border-radius: 8px;
}

.symbol-input :deep(.el-input__inner) {
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
}

.symbol-suggestion-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 4px 0;
}

.symbol-name {
  font-weight: 500;
  font-size: 14px;
}
</style>
