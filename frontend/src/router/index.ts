import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import AlertList from '@/views/AlertList.vue'
import SymbolManage from '@/views/SymbolManage.vue'
import SymbolMonitor from '@/views/SymbolMonitor.vue'
import Settings from '@/views/Settings.vue'
import LogViewer from '@/views/LogViewer.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Dashboard', component: Dashboard, meta: { title: '监控仪表盘' } },
  { path: '/monitor', name: 'SymbolMonitor', component: SymbolMonitor, meta: { title: '交易对监控' } },
  { path: '/alerts', name: 'AlertList', component: AlertList, meta: { title: '提醒记录' } },
  { path: '/symbols', name: 'SymbolManage', component: SymbolManage, meta: { title: '交易对管理' } },
  { path: '/logs', name: 'LogViewer', component: LogViewer, meta: { title: '日志查看' } },
  { path: '/settings', name: 'Settings', component: Settings, meta: { title: '参数设置' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
