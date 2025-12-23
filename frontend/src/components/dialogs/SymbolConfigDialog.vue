<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑交易对配置' : '添加交易对配置'"
    width="480px"
    class="unified-dialog"
    align-center
    center
    :show-close="false"
  >
    <el-form :model="form" label-width="140px">
      <el-form-item label="选择交易对" v-if="!isEdit">
        <el-select
          v-model="form.symbol"
          filterable
          placeholder="请选择交易对"
          style="width: 100%;"
        >
          <el-option
            v-for="symbol in availableSymbols"
            :key="symbol"
            :label="symbol"
            :value="symbol"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="交易对" v-else>
        <el-input v-model="form.symbol" disabled />
      </el-form-item>
      <el-form-item label="K线间隔" v-if="!isEdit">
        <el-select v-model="form.interval" placeholder="请选择K线间隔" style="width: 100%;">
          <el-option v-for="item in intervalOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="K线间隔" v-else>
        <el-input v-model="form.interval" disabled />
      </el-form-item>
      <el-form-item label="开盘价误差 (%)">
        <el-input-number
          v-model="form.price_error"
          :min="0.1"
          :max="10"
          :precision="1"
          :step="0.1"
          :controls="false"
          style="width: 100%;"
          placeholder="留空使用全局配置"
        />
      </el-form-item>
      <el-form-item label="最小间隔K线数">
        <el-input-number
          v-model="form.middle_kline_cnt"
          :min="0"
          :max="100"
          :precision="0"
          :controls="false"
          style="width: 100%;"
          placeholder="留空使用全局配置"
        />
      </el-form-item>
      <el-form-item label="假K线数量">
        <el-input-number
          v-model="form.fake_kline_cnt"
          :min="1"
          :max="50"
          :precision="0"
          :controls="false"
          style="width: 100%;"
          placeholder="留空使用全局配置"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleCancel" size="large">取消</el-button>
      <el-button type="primary" @click="handleConfirm" :loading="loading" size="large">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { SymbolConfig } from '@/types'

const visible = defineModel<boolean>({ default: false })

const props = defineProps<{
  isEdit: boolean
  editConfig?: SymbolConfig | null
  defaultPriceError: number
  defaultMiddleKlineCnt: number
  defaultFakeKlineCnt: number
  availableSymbols: string[]
  loading?: boolean
}>()

const emit = defineEmits<{
  confirm: [data: {
    symbol: string
    interval: string
    price_error: number | null
    middle_kline_cnt: number | null
    fake_kline_cnt: number | null
  }]
  cancel: []
}>()

const intervalOptions = [
  { label: '15分钟', value: '15m' },
  { label: '30分钟', value: '30m' },
  { label: '1小时', value: '1h' },
  { label: '4小时', value: '4h' },
  { label: '1天', value: '1d' },
  { label: '3天', value: '3d' }
]

const form = reactive({
  symbol: '',
  interval: '15m',
  price_error: null as number | null,
  middle_kline_cnt: null as number | null,
  fake_kline_cnt: null as number | null
})

watch(visible, (val) => {
  if (val) {
    if (props.isEdit && props.editConfig) {
      form.symbol = props.editConfig.symbol
      form.interval = props.editConfig.interval
      form.price_error = props.editConfig.price_error
      form.middle_kline_cnt = props.editConfig.middle_kline_cnt
      form.fake_kline_cnt = props.editConfig.fake_kline_cnt
    } else {
      form.symbol = ''
      form.interval = '15m'
      form.price_error = props.defaultPriceError
      form.middle_kline_cnt = props.defaultMiddleKlineCnt
      form.fake_kline_cnt = props.defaultFakeKlineCnt
    }
  }
})

const handleConfirm = () => {
  if (!form.symbol || !form.interval) return
  emit('confirm', {
    symbol: form.symbol,
    interval: form.interval,
    price_error: form.price_error,
    middle_kline_cnt: form.middle_kline_cnt,
    fake_kline_cnt: form.fake_kline_cnt
  })
}

const handleCancel = () => {
  visible.value = false
  emit('cancel')
}
</script>

<style>
@import '@/styles/dialog.css';
</style>
