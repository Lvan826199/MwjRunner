<template>
  <div class="executions-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px" @change="loadExecutions">
        <el-option label="执行中" value="running" />
        <el-option label="通过" value="passed" />
        <el-option label="失败" value="failed" />
        <el-option label="错误" value="error" />
      </el-select>
      <el-button :icon="Refresh" @click="loadExecutions">刷新</el-button>
    </div>

    <!-- 执行记录表格 -->
    <el-table :data="executions" stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="case_name" label="用例名称" min-width="180" />
      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small" effect="dark">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="用例统计" width="160">
        <template #default="{ row }">
          <span class="stat-text">
            <span class="stat-pass">{{ row.passed_cases }}</span> /
            <span class="stat-fail">{{ row.failed_cases }}</span> /
            <span>{{ row.total_cases }}</span>
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="elapsed_ms" label="耗时" width="100" align="right">
        <template #default="{ row }">
          {{ row.elapsed_ms > 0 ? `${row.elapsed_ms.toFixed(0)}ms` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="started_at" label="开始时间" width="170">
        <template #default="{ row }">
          {{ row.started_at ? formatTime(row.started_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="viewDetail(row)">详情</el-button>
          <el-button size="small" text type="info" @click="viewReport(row)">报告</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情抽屉 -->
    <el-drawer v-model="showDetail" title="执行详情" size="600px">
      <template v-if="currentExecution">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="运行ID">{{ currentExecution.run_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(currentExecution.status)" size="small">
              {{ statusLabel(currentExecution.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="退出码">{{ currentExecution.exit_code ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ currentExecution.elapsed_ms.toFixed(0) }}ms</el-descriptions-item>
          <el-descriptions-item label="用例">
            通过 {{ currentExecution.passed_cases }} / 失败 {{ currentExecution.failed_cases }} / 总计 {{ currentExecution.total_cases }}
          </el-descriptions-item>
          <el-descriptions-item label="断言">
            失败 {{ currentExecution.failed_assertions }} / 总计 {{ currentExecution.total_assertions }}
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="currentExecution.stdout" style="margin-top: 16px">
          <h4>控制台输出</h4>
          <el-input type="textarea" :model-value="currentExecution.stdout" :rows="12" readonly />
        </div>
        <div v-if="currentExecution.stderr" style="margin-top: 12px">
          <h4>错误输出</h4>
          <el-input type="textarea" :model-value="currentExecution.stderr" :rows="4" readonly />
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { executionApi, type Execution } from '../api'

const executions = ref<Execution[]>([])
const loading = ref(false)
const filterStatus = ref('')
const showDetail = ref(false)
const currentExecution = ref<Execution | null>(null)

onMounted(() => {
  loadExecutions()
})

async function loadExecutions() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await executionApi.list(params)
    executions.value = data
  } finally {
    loading.value = false
  }
}

async function viewDetail(row: Execution) {
  const { data } = await executionApi.get(row.id)
  currentExecution.value = data
  showDetail.value = true
}

function viewReport(row: Execution) {
  ElMessage.info('报告查看功能开发中')
}

function statusType(s: string) {
  if (s === 'passed') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'error') return 'warning'
  if (s === 'running') return ''
  return 'info'
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    running: '执行中', passed: '通过', failed: '失败', error: '错误', timeout: '超时',
  }
  return map[s] || s
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style scoped>
.executions-page {
  padding: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-text {
  font-size: 13px;
}
.stat-pass {
  color: #67c23a;
  font-weight: 500;
}
.stat-fail {
  color: #f56c6c;
  font-weight: 500;
}
</style>
