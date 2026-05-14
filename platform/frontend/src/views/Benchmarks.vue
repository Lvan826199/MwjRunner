<template>
  <div class="benchmarks-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="showCreate = true">新建压测</el-button>
      <el-button :icon="Refresh" @click="loadList">刷新</el-button>
    </div>

    <!-- 压测记录列表 -->
    <el-table :data="benchmarks" v-loading="loading" stripe>
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small" effect="dark">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
      <el-table-column label="目标" min-width="200">
        <template #default="{ row }">
          <el-tag size="small" effect="plain" style="margin-right: 4px">{{ row.method }}</el-tag>
          <span class="target-url">{{ row.target_url }}</span>
        </template>
      </el-table-column>
      <el-table-column label="并发/总数" width="100" align="center">
        <template #default="{ row }">{{ row.concurrency }} / {{ row.total_requests }}</template>
      </el-table-column>
      <el-table-column label="RPS" width="80" align="center">
        <template #default="{ row }">
          <span class="metric-value">{{ row.rps ? row.rps.toFixed(1) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Avg(ms)" width="80" align="center">
        <template #default="{ row }">{{ row.avg_latency_ms ? row.avg_latency_ms.toFixed(1) : '-' }}</template>
      </el-table-column>
      <el-table-column label="P95(ms)" width="80" align="center">
        <template #default="{ row }">{{ row.p95_latency_ms ? row.p95_latency_ms.toFixed(1) : '-' }}</template>
      </el-table-column>
      <el-table-column label="成功率" width="80" align="center">
        <template #default="{ row }">
          <span v-if="row.total_sent" :class="successRateClass(row)">
            {{ ((row.success_count / row.total_sent) * 100).toFixed(1) }}%
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text :icon="View" @click="openDetail(row)">详情</el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" text type="danger" :icon="Delete">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建压测对话框 -->
    <el-dialog v-model="showCreate" title="新建性能压测" width="520px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如：用户列表接口压测" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="方法">
              <el-select v-model="form.method" style="width: 100%">
                <el-option v-for="m in ['GET','POST','PUT','DELETE']" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="18">
            <el-form-item label="目标 URL">
              <el-input v-model="form.target_url" placeholder="http://localhost:8000/api/users" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="并发数">
              <el-input-number v-model="form.concurrency" :min="1" :max="500" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="总请求数">
              <el-input-number v-model="form.total_requests" :min="1" :max="100000" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="请求 Headers">
          <el-input v-model="form.headers" type="textarea" :rows="2" placeholder='{"Authorization": "Bearer xxx"}' />
        </el-form-item>
        <el-form-item label="请求 Body">
          <el-input v-model="form.body" type="textarea" :rows="3" placeholder="POST/PUT 请求体" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">开始压测</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="showDetail" title="压测详情" size="480px">
      <template v-if="detail">
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-grid">
            <div class="detail-item"><span class="label">名称</span><span>{{ detail.name }}</span></div>
            <div class="detail-item"><span class="label">目标</span><span>{{ detail.method }} {{ detail.target_url }}</span></div>
            <div class="detail-item"><span class="label">并发/总数</span><span>{{ detail.concurrency }} / {{ detail.total_requests }}</span></div>
            <div class="detail-item"><span class="label">耗时</span><span>{{ (detail.elapsed_ms / 1000).toFixed(2) }}s</span></div>
          </div>
        </div>
        <div class="detail-section">
          <h4>延迟分布</h4>
          <div class="latency-grid">
            <div class="latency-item">
              <span class="latency-label">Min</span>
              <span class="latency-value">{{ detail.min_latency_ms.toFixed(1) }}ms</span>
            </div>
            <div class="latency-item">
              <span class="latency-label">P50</span>
              <span class="latency-value">{{ detail.p50_latency_ms.toFixed(1) }}ms</span>
            </div>
            <div class="latency-item">
              <span class="latency-label">P90</span>
              <span class="latency-value">{{ detail.p90_latency_ms.toFixed(1) }}ms</span>
            </div>
            <div class="latency-item">
              <span class="latency-label">P95</span>
              <span class="latency-value latency-value--warn">{{ detail.p95_latency_ms.toFixed(1) }}ms</span>
            </div>
            <div class="latency-item">
              <span class="latency-label">P99</span>
              <span class="latency-value latency-value--danger">{{ detail.p99_latency_ms.toFixed(1) }}ms</span>
            </div>
            <div class="latency-item">
              <span class="latency-label">Max</span>
              <span class="latency-value latency-value--danger">{{ detail.max_latency_ms.toFixed(1) }}ms</span>
            </div>
          </div>
        </div>
        <div class="detail-section">
          <h4>吞吐量</h4>
          <div class="throughput-row">
            <div class="throughput-card">
              <div class="throughput-value">{{ detail.rps.toFixed(1) }}</div>
              <div class="throughput-label">RPS</div>
            </div>
            <div class="throughput-card">
              <div class="throughput-value throughput-value--success">{{ detail.success_count }}</div>
              <div class="throughput-label">成功</div>
            </div>
            <div class="throughput-card">
              <div class="throughput-value throughput-value--danger">{{ detail.fail_count }}</div>
              <div class="throughput-label">失败</div>
            </div>
          </div>
        </div>
        <div v-if="errorDist && Object.keys(errorDist).length" class="detail-section">
          <h4>错误分布</h4>
          <el-tag v-for="(count, key) in errorDist" :key="key" type="danger" effect="plain" style="margin: 4px">
            {{ key }}: {{ count }}
          </el-tag>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus, Refresh, View, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { benchmarkApi, type Benchmark } from '../api'

const benchmarks = ref<Benchmark[]>([])
const loading = ref(false)
const creating = ref(false)
const showCreate = ref(false)
const showDetail = ref(false)
const detail = ref<Benchmark | null>(null)

const form = ref({
  name: '',
  target_url: '',
  method: 'GET',
  concurrency: 10,
  total_requests: 100,
  headers: '',
  body: '',
})

const errorDist = computed(() => {
  if (!detail.value) return {}
  try { return JSON.parse(detail.value.error_distribution) } catch { return {} }
})

onMounted(() => loadList())

async function loadList() {
  loading.value = true
  try {
    const { data } = await benchmarkApi.list()
    benchmarks.value = data
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!form.value.name || !form.value.target_url) {
    ElMessage.warning('请填写名称和目标 URL')
    return
  }
  creating.value = true
  try {
    await benchmarkApi.create(form.value)
    ElMessage.success('压测已启动')
    showCreate.value = false
    form.value = { name: '', target_url: '', method: 'GET', concurrency: 10, total_requests: 100, headers: '', body: '' }
    loadList()
  } finally {
    creating.value = false
  }
}

async function handleDelete(id: number) {
  await benchmarkApi.delete(id)
  ElMessage.success('已删除')
  loadList()
}

function openDetail(row: Benchmark) {
  detail.value = row
  showDetail.value = true
}

function statusType(s: string) {
  const map: Record<string, string> = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' }
  return (map[s] || 'info') as 'info' | 'warning' | 'success' | 'danger'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '等待', running: '运行中', completed: '完成', failed: '失败' }
  return map[s] || s
}

function successRateClass(row: Benchmark) {
  const rate = row.success_count / row.total_sent
  if (rate >= 0.99) return 'rate--good'
  if (rate >= 0.95) return 'rate--warn'
  return 'rate--bad'
}
</script>

<style scoped>
.benchmarks-page { padding: 0; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.target-url { font-size: 12px; color: #606266; }
.metric-value { font-weight: 600; color: #409eff; }
.rate--good { color: #67c23a; font-weight: 600; }
.rate--warn { color: #e6a23c; font-weight: 600; }
.rate--bad { color: #f56c6c; font-weight: 600; }

/* 详情抽屉 */
.detail-section { margin-bottom: 24px; }
.detail-section h4 { margin: 0 0 12px; font-size: 14px; color: #303133; }
.detail-grid { display: grid; gap: 8px; }
.detail-item { display: flex; gap: 8px; font-size: 13px; }
.detail-item .label { color: #909399; min-width: 70px; }

.latency-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.latency-item {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}
.latency-label { display: block; font-size: 12px; color: #909399; margin-bottom: 4px; }
.latency-value { font-size: 16px; font-weight: 600; color: #303133; }
.latency-value--warn { color: #e6a23c; }
.latency-value--danger { color: #f56c6c; }

.throughput-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.throughput-card { background: #f5f7fa; border-radius: 6px; padding: 16px; text-align: center; }
.throughput-value { font-size: 20px; font-weight: 600; color: #409eff; }
.throughput-value--success { color: #67c23a; }
.throughput-value--danger { color: #f56c6c; }
.throughput-label { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
