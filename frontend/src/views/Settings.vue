<template>
  <div class="page-wrapper settings-page">
    <div class="page-content settings-content">
      <el-form ref="formRef" :model="form" :rules="rules" v-loading="loading" class="settings-form">
        
        <!-- Main Settings Container -->
        <el-card class="main-settings-card" shadow="never">
          
          <!-- Global Strategy Section -->
          <div class="settings-section">
            <div class="section-header">
              <div class="header-icon-wrapper bg-blue">
                <el-icon><Operation /></el-icon>
              </div>
              <div class="header-text">
                <span class="section-title">全局策略配置</span>
                <span class="section-subtitle">配置适用于所有币种的基础监控参数和匹配规则</span>
              </div>
            </div>

            <div class="params-grid">
              <!-- Volume Group -->
              <div class="param-group">
                <div class="group-label">
                  <el-icon><DataLine /></el-icon>
                  <span>成交量监控</span>
                </div>
                <div class="monitor-params-row">
                  <div class="param-item">
                    <span class="param-label">触发阈值</span>
                    <div class="param-input-wrapper">
                      <el-input-number 
                        v-model="form.volume_percent" 
                        :min="0.1" :max="100" :precision="1" :step="0.5" :controls="false"
                        size="large"
                        class="unified-input"
                      />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="param-item">
                    <span class="param-label">提醒间隔</span>
                    <div class="param-input-wrapper">
                      <el-input-number 
                        v-model="form.volume_reminder_interval" 
                        :min="0" :max="1440" :precision="0" :controls="false"
                        size="large"
                        class="unified-input"
                      />
                      <span class="unit">分</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Rise Group -->
              <div class="param-group">
                <div class="group-label">
                  <el-icon><TrendCharts /></el-icon>
                  <span>涨幅监控</span>
                </div>
                <div class="monitor-params-row">
                  <div class="param-item">
                    <span class="param-label">触发阈值</span>
                    <div class="param-input-wrapper">
                      <el-input-number 
                        v-model="form.rise_threshold" 
                        :min="1" :max="100" :precision="1" :step="0.5" :controls="false"
                        size="large"
                        class="unified-input"
                      />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="param-item">
                    <span class="param-label">提醒间隔</span>
                    <div class="param-input-wrapper">
                      <el-input-number 
                        v-model="form.rise_reminder_interval" 
                        :min="0" :max="1440" :precision="0" :controls="false"
                        size="large"
                        class="unified-input"
                      />
                      <span class="unit">分</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Price Match Group -->
              <div class="param-group wide-group">
                <div class="group-label">
                  <el-icon><Connection /></el-icon>
                  <span>开盘价匹配规则</span>
                </div>
                <div class="wide-params-container">
                  <div class="param-item">
                    <span class="param-label">开盘价误差</span>
                    <div class="param-input-wrapper">
                      <el-input-number 
                        v-model="form.price_error" 
                        :min="0.1" :max="10" :precision="1" :step="0.1" :controls="false"
                        size="large"
                        class="unified-input"
                      />
                      <span class="unit">%</span>
                    </div>
                  </div>
                  <div class="param-item">
                    <span class="param-label">最小间隔K线</span>
                    <div class="param-input-wrapper">
                      <el-input-number 
                        v-model="form.middle_kline_cnt" 
                        :min="0" :max="100" :precision="0" :controls="false"
                        class="unified-input"
                      />
                      <span class="unit">根</span>
                    </div>
                  </div>
                  <div class="param-item">
                    <span class="param-label">假K线容忍</span>
                    <div class="param-input-wrapper">
                      <el-input-number 
                        v-model="form.fake_count_n" 
                        :min="1" :max="50" :precision="0" :controls="false"
                        size="large"
                        class="unified-input"
                      />
                      <span class="unit">根</span>
                    </div>
                  </div>
                  <div class="param-item">
                    <span class="param-label">去重控制</span>
                    <div class="param-input-wrapper">
                      <el-switch v-model="form.dedup_type3_enabled" size="large" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <el-divider class="section-divider" />

          <!-- Symbol Configuration Section -->
          <div class="settings-section">
            <div class="section-header is-between">
              <div class="header-left">
                <div class="header-icon-wrapper bg-green">
                  <el-icon><Setting /></el-icon>
                </div>
                <div class="header-text">
                  <span class="section-title">币种个性化配置</span>
                  <span class="section-subtitle">为特定币种设置独立的参数，优先级高于全局配置</span>
                </div>
              </div>
              <el-button type="primary" plain round @click="showAddSymbolConfig" size="small">
                <el-icon class="el-icon--left"><Plus /></el-icon>
                添加配置
              </el-button>
            </div>

            <div class="table-container">
              <el-table 
                :data="symbolConfigs" 
                v-loading="symbolConfigLoading" 
                style="width: 100%;" 
                size="large"
                :header-cell-style="{ background: 'var(--bg-color-overlay)', color: 'var(--text-color-regular)', fontWeight: '600' }"
              >
                <el-table-column prop="symbol" label="币种" width="140">
                  <template #default="{ row }">
                    <span class="symbol-text">{{ row.symbol }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="interval" label="K线间隔" width="120">
                  <template #default="{ row }">
                    <el-tag effect="light" round>{{ row.interval }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="price_error" label="开盘价误差">
                  <template #default="{ row }">
                    <span :class="row.price_error !== null ? 'value-highlight' : 'value-default'">
                      {{ row.price_error !== null ? row.price_error + '%' : '全局' }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="middle_kline_cnt" label="最小间隔K线">
                  <template #default="{ row }">
                    <span :class="row.middle_kline_cnt !== null ? 'value-highlight' : 'value-default'">
                      {{ row.middle_kline_cnt !== null ? row.middle_kline_cnt : '全局' }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="fake_kline_cnt" label="假K线数量">
                  <template #default="{ row }">
                    <span :class="row.fake_kline_cnt !== null ? 'value-highlight' : 'value-default'">
                      {{ row.fake_kline_cnt !== null ? row.fake_kline_cnt : '全局' }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="140" align="right">
                  <template #default="{ row }">
                    <el-button type="primary" link @click="editSymbolConfig(row)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                    <el-button type="danger" link @click="removeSymbolConfig(row)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
                <template #empty>
                  <div class="empty-state">
                    <el-icon class="empty-icon"><Setting /></el-icon>
                    <p>暂无个性化配置</p>
                  </div>
                </template>
              </el-table>
            </div>
          </div>

        </el-card>
      </el-form>
    </div>

    <div class="settings-footer">
      <div class="footer-content">
        <el-button @click="fetchConfigs" :disabled="saving">重置更改</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving" size="large" class="save-btn">
          <el-icon class="el-icon--left"><Check /></el-icon>
          保存所有配置
        </el-button>
      </div>
    </div>

    <!-- 币种配置弹窗 -->
    <SymbolConfigDialog
      v-model="symbolConfigDialogVisible"
      :is-edit="editingSymbolConfig"
      :edit-config="editingConfig"
      :default-price-error="form.price_error"
      :default-middle-kline-cnt="form.middle_kline_cnt"
      :default-fake-kline-cnt="form.fake_count_n"
      :available-symbols="availableSymbols"
      :loading="symbolConfigSaving"
      @confirm="saveSymbolConfig"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getConfigs, batchUpdateConfigs, getSymbolConfigs, updateSymbolConfig, deleteSymbolConfig, getSymbols } from '@/api'
import type { SymbolConfig } from '@/types'
import type { FormInstance, FormRules } from 'element-plus'
import { DataLine, TrendCharts, Connection, Check, Setting, Plus, Edit, Delete, Operation } from '@element-plus/icons-vue'
import SymbolConfigDialog from '@/components/dialogs/SymbolConfigDialog.vue'
import { logger } from '@/utils/logger'

const formRef = ref<FormInstance>()
const loading = ref(false)
const saving = ref(false)

const form = reactive({
  volume_percent: 12.5,
  volume_reminder_interval: 60,
  rise_threshold: 10,
  rise_reminder_interval: 60,
  price_error: 1,
  middle_kline_cnt: 3,
  fake_count_n: 5,
  dedup_type3_enabled: true
})

const rules: FormRules = {
  volume_percent: [{ required: true, message: '请输入成交量百分比' }],
  rise_threshold: [{ required: true, message: '请输入涨幅阈值' }],
  price_error: [{ required: true, message: '请输入开盘价误差' }],
  fake_count_n: [{ required: true, message: '请输入假K线数量' }]
}

const symbolConfigs = ref<SymbolConfig[]>([])
const symbolConfigLoading = ref(false)
const symbolConfigDialogVisible = ref(false)
const symbolConfigSaving = ref(false)
const editingSymbolConfig = ref(false)
const editingConfig = ref<SymbolConfig | null>(null)
const allSymbols = ref<string[]>([])

const availableSymbols = computed(() => {
  return allSymbols.value
})

// 配置键名映射：后端key -> 前端form字段
const configKeyMap: Record<string, string> = {
  '1_volume_percent': 'volume_percent',
  '1_reminder_interval': 'volume_reminder_interval',
  '2_rise_percent': 'rise_threshold',
  '2_reminder_interval': 'rise_reminder_interval',
  '3_price_error': 'price_error',
  '3_middle_kline_cnt': 'middle_kline_cnt',
  '3_fake_kline_cnt': 'fake_count_n',
  '3_dedup_enabled': 'dedup_type3_enabled'
}

const fetchConfigs = async () => {
  loading.value = true
  try {
    const data = await getConfigs()
    data.forEach(c => {
      const formKey = configKeyMap[c.key]
      if (formKey) {
        if (formKey === 'dedup_type3_enabled') {
          (form as any)[formKey] = c.value.toLowerCase() === 'true'
        } else {
          (form as any)[formKey] = parseFloat(c.value)
        }
      }
    })
  } catch {
    ElMessage.error('获取配置失败')
  } finally {
    loading.value = false
  }
}

const fetchSymbolConfigs = async () => {
  symbolConfigLoading.value = true
  try {
    const data = await getSymbolConfigs({ limit: 500 })
    symbolConfigs.value = data.items
  } catch (error) {
    logger.error('获取币种配置失败', error, { sampling: 10000 })
  } finally {
    symbolConfigLoading.value = false
  }
}

const fetchAllSymbols = async () => {
  try {
    const data = await getSymbols({ limit: 500, is_active: true })
    allSymbols.value = data.items.map(s => s.symbol)
  } catch (error) {
    logger.error('获取币种列表失败', error, { sampling: 10000 })
  }
}

const showAddSymbolConfig = () => {
  editingSymbolConfig.value = false
  editingConfig.value = null
  symbolConfigDialogVisible.value = true
}

const editSymbolConfig = (config: SymbolConfig) => {
  editingSymbolConfig.value = true
  editingConfig.value = config
  symbolConfigDialogVisible.value = true
}

const saveSymbolConfig = async (data: {
  symbol: string
  interval: string
  price_error: number | null
  middle_kline_cnt: number | null
  fake_kline_cnt: number | null
}) => {
  if (!data.symbol || !data.interval) {
    ElMessage.warning('请选择币种和K线间隔')
    return
  }
  symbolConfigSaving.value = true
  try {
    await updateSymbolConfig(data.symbol, data.interval, {
      price_error: data.price_error,
      middle_kline_cnt: data.middle_kline_cnt,
      fake_kline_cnt: data.fake_kline_cnt
    })
    ElMessage.success('保存成功')
    symbolConfigDialogVisible.value = false
    fetchSymbolConfigs()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    symbolConfigSaving.value = false
  }
}

const removeSymbolConfig = async (config: SymbolConfig) => {
  try {
    await ElMessageBox.confirm(
      `确定删除 ${config.symbol} (${config.interval}) 的个性化配置吗？删除后将使用全局配置。`,
      '确认删除',
      { type: 'warning' }
    )
    await deleteSymbolConfig(config.symbol, config.interval)
    ElMessage.success('删除成功')
    fetchSymbolConfigs()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const configs = [
      { key: '1_volume_percent', value: String(form.volume_percent) },
      { key: '1_reminder_interval', value: String(form.volume_reminder_interval) },
      { key: '2_rise_percent', value: String(form.rise_threshold) },
      { key: '2_reminder_interval', value: String(form.rise_reminder_interval) },
      { key: '3_price_error', value: String(form.price_error) },
      { key: '3_middle_kline_cnt', value: String(form.middle_kline_cnt) },
      { key: '3_fake_kline_cnt', value: String(form.fake_count_n) },
      { key: '3_dedup_enabled', value: String(form.dedup_type3_enabled).toLowerCase() }
    ]
    await batchUpdateConfigs(configs)
    ElMessage.success('配置保存成功')
  } catch {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfigs()
  fetchSymbolConfigs()
  fetchAllSymbols()
})
</script>

<style scoped>
.settings-page {
  position: relative;
  overflow: hidden;
}

.settings-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 80px; /* Space for footer */
}

.settings-form {
  width: 100%;
}

.main-settings-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color-lighter);
  overflow: hidden;
  background: #fff;
  width: 100%;
}

.main-settings-card :deep(.el-card__body) {
  padding: 0;
}

.settings-section {
  padding: 24px 32px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.section-header.is-between {
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.bg-blue { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.bg-green { background: rgba(103, 194, 58, 0.12); color: var(--el-color-success); }

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-primary);
  display: block;
  margin-bottom: 4px;
}

.section-subtitle {
  font-size: 13px;
  color: var(--text-color-secondary);
}

.params-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.param-group {
  background: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 20px;
  transition: all 0.3s ease;
}

.param-group:hover {
  background: #fff;
  border-color: var(--el-color-primary-light-8);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
  transform: translateY(-2px);
}

.monitor-params-row {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.param-group.wide-group {
  /* No special handling needed for vertical layout */
}

.group-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  color: var(--text-color-primary);
  font-size: 16px;
  margin-bottom: 4px;
}

.wide-params-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color-regular);
  margin-bottom: 6px;
}

.param-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unified-input {
  width: 100%;
}

.unit {
  font-size: 13px;
  color: var(--text-color-secondary);
  white-space: nowrap;
}

.section-divider {
  margin: 0;
  border-color: var(--border-color-lighter);
}

.table-container {
  border: 1px solid var(--border-color-lighter);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.symbol-text {
  font-weight: 600;
  color: var(--text-color-primary);
}

.value-highlight {
  color: var(--el-color-primary);
  font-weight: 600;
}

.value-default {
  color: var(--text-color-secondary);
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-color-secondary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.settings-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--border-color-lighter);
  display: flex;
  justify-content: flex-end;
  z-index: 10;
}

.footer-content {
  display: flex;
  gap: 16px;
  max-width: 100%;
  width: 100%;
  justify-content: flex-end;
  margin: 0 auto;
  padding: 0 32px;
}

.save-btn {
  padding-left: 24px;
  padding-right: 24px;
}

/* Custom Input Styles */
:deep(.el-input-number .el-input__wrapper) {
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--border-color-light) inset;
  padding-left: 12px;
  padding-right: 12px;
}

:deep(.el-input-number .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-color-base) inset;
}

:deep(.el-input-number .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(25, 103, 210, 0.18) !important;
}

/* Responsive */
@media screen and (max-width: 600px) {
  .section-header.is-between {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-left {
    width: 100%;
    margin-bottom: 12px;
  }
  
  .settings-section {
    padding: 16px 20px;
  }
}
</style>
