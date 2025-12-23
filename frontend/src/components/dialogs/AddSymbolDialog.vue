<template>
  <el-dialog
    v-model="visible"
    title="添加交易对"
    width="420px"
    destroy-on-close
    class="add-symbol-dialog unified-dialog"
    center
    align-center
    :show-close="false"
  >
    <div class="add-dialog-content">
      <div class="dialog-icon-wrapper">
        <el-icon :size="40" color="var(--el-color-primary)"><Coin /></el-icon>
      </div>
      <p class="dialog-instruction">请输入 Binance 交易对</p>
      <el-form :model="form" @submit.prevent="handleSubmit" size="large" style="width: 100%">
        <el-form-item style="margin-bottom: 16px">
          <el-input
            v-model="form.symbol"
            placeholder="例如：BTCUSDT"
            @keyup.enter="handleSubmit"
            class="symbol-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
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
import { ref, reactive, watch } from 'vue'
import { Coin, Search } from '@element-plus/icons-vue'

const visible = defineModel<boolean>({ default: false })

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  confirm: [symbol: string]
  cancel: []
}>()

const form = reactive({ symbol: '' })

watch(visible, (val) => {
  if (val) {
    form.symbol = ''
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

</style>
