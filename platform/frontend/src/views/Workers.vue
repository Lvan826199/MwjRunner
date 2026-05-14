<template>
  <div class="workers-page">
    <!-- 概览统计 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-card__value stat-card__value--primary">{{ workers.length }}</div>
        <div class="stat-card__label">总节点</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__value stat-card__value--success">{{ onlineCount }}</div>
        <div class="stat-card__label">在线</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__value stat-card__value--warning">{{ busyCount }}</div>
        <div class="stat-card__label">忙碌</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__value stat-card__value--danger">{{ offlineCount }}</div>
        <div class="stat-card__label">离线</div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button :icon="Refresh" @click="loadWorkers">刷新</el-button>
      <span class="toolbar__hint">Worker 通过 API 自注册，心跳超时 60 秒自动标记离线</span>
    </div>

    <!-- Worker 节点列表 -->
    <div class="worker-grid" v-loading="loading">
      <div
        v-for="w in workers"
        :key="w.id"
        class="worker-card"
        :class="`worker-card--${w.status}`"
      >
        <div class="worker-card__header">
          <div class="worker-card__status">
            <span class="status-dot" :class="`dot--${w.status}`" />
            <span class="status-text">{{ statusLabel(w.status) }}</span>
          </div>
          <el-popconfirm title="确定移除该 Worker？" @confirm="removeWorker(w.worker_id)">
            <template #reference>
              <el-button size="small" text type="danger" :icon="Delete" @click.stop />
            </template>
          </el-popconfirm>
        </div>

        <div class="worker-card__body">
          <div class="worker-card__name">{{ w.name || w.worker_id }}</div>
          <div class="worker-card__host">{{ w.host }}{{ w.port ? `:${w.port}` : '' }}</div>
        </div>

        <div class="worker-card__metrics">
          <div class="metric">
            <span class="metric__label">并发上限</span>
            <span class="metric__value">{{ w.max_concurrency }}</span>
          </div>
          <div class="metric">
            <span class="metric__label">当前任务</span>
            <span class="metric__value" :class="{ 'metric__value--busy': w.current_tasks > 0 }">
              {{ w.current_tasks }}
            </span>
          </div>
          <div class="metric">
            <span class="metric__label">最后心跳</span>
            <span class="metric__value metric__value--time">{{ formatHeartbeat(w.last_heartbeat) }}</span>
          </div>
        </div>

        <div v-if="w.tags" class="worker-card__tags">
          <el-tag v-for="tag in w.tags.split(',')" :key="tag" size="small" effect="plain">
            {{ tag.trim() }}
          </el-tag>
        </div>
      </div>

      <div v-if="!loading && workers.length === 0" class="worker-empty">
        <el-empty description="暂无 Worker 节点注册">
          <template #description>
            <p>Worker 通过 POST /api/workers/register 自注册</p>
          </template>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Refresh, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { workerApi, type Worker } from '../api'

const workers = ref<Worker[]>([])
const loading = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const onlineCount = computed(() => workers.value.filter(w => w.status === 'online').length)
const busyCount = computed(() => workers.value.filter(w => w.status === 'busy').length)
const offlineCount = computed(() => workers.value.filter(w => w.status === 'offline').length)

onMounted(() => {
  loadWorkers()
  // 每 10 秒自动刷新
  refreshTimer = setInterval(loadWorkers, 10000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

async function loadWorkers() {
  loading.value = true
  try {
    const { data } = await workerApi.list()
    workers.value = data
  } finally {
    loading.value = false
  }
}

async function removeWorker(workerId: string) {
  await workerApi.remove(workerId)
  ElMessage.success('Worker 已移除')
  loadWorkers()
}

function statusLabel(s: string) {
  const map: Record<string, string> = { online: '在线', offline: '离线', busy: '忙碌' }
  return map[s] || s
}

function formatHeartbeat(t: string | null) {
  if (!t) return '-'
  const diff = Math.floor((Date.now() - new Date(t).getTime()) / 1000)
  if (diff < 10) return '刚刚'
  if (diff < 60) return `${diff}秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  return `${Math.floor(diff / 3600)}小时前`
}
</script>

<style scoped>
.workers-page {
  padding: 0;
}

/* 统计行 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}
.stat-card__value {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.2;
}
.stat-card__value--primary { color: #409eff; }
.stat-card__value--success { color: #67c23a; }
.stat-card__value--warning { color: #e6a23c; }
.stat-card__value--danger { color: #f56c6c; }
.stat-card__label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.toolbar__hint {
  font-size: 12px;
  color: #909399;
}

/* Worker 卡片网格 */
.worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.worker-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #ebeef5;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s, border-color 0.2s;
  cursor: default;
}
.worker-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.worker-card--online {
  border-left: 3px solid #67c23a;
}
.worker-card--busy {
  border-left: 3px solid #e6a23c;
}
.worker-card--offline {
  border-left: 3px solid #c0c4cc;
  opacity: 0.7;
}

.worker-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.worker-card__status {
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot--online {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.5);
  animation: pulse-green 2s infinite;
}
.dot--busy {
  background: #e6a23c;
  box-shadow: 0 0 6px rgba(230, 162, 60, 0.5);
}
.dot--offline {
  background: #c0c4cc;
}
.status-text {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.worker-card__body {
  margin-bottom: 12px;
}
.worker-card__name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}
.worker-card__host {
  font-size: 12px;
  color: #909399;
  font-family: 'Fira Code', monospace;
}

.worker-card__metrics {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding: 10px 0;
  border-top: 1px solid #f5f5f5;
}
.metric {
  text-align: center;
}
.metric__label {
  display: block;
  font-size: 11px;
  color: #909399;
  margin-bottom: 2px;
}
.metric__value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
.metric__value--busy {
  color: #e6a23c;
}
.metric__value--time {
  font-size: 11px;
  color: #606266;
}

.worker-card__tags {
  margin-top: 10px;
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.worker-empty {
  grid-column: 1 / -1;
}

@keyframes pulse-green {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
