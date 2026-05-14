<template>
  <div class="execution-detail" v-loading="loading">
    <el-page-header @back="$router.push('/executions')">
      <template #content>
        <span>执行详情 - {{ execution?.case_name }}</span>
        <el-tag :type="statusType" style="margin-left: 12px">{{ execution?.status }}</el-tag>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px" v-if="execution">
      <!-- 基本信息 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>基本信息</template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="Run ID">{{ execution.run_id }}</el-descriptions-item>
            <el-descriptions-item label="环境">{{ execution.env_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="并发数">{{ execution.workers }}</el-descriptions-item>
            <el-descriptions-item label="标签">{{ execution.tags || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ execution.started_at }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ execution.finished_at || '进行中' }}</el-descriptions-item>
            <el-descriptions-item label="耗时">{{ (execution.elapsed_ms / 1000).toFixed(2) }}s</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 统计 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>执行统计</template>
          <v-chart :option="resultPieOption" style="height: 200px" autoresize />
          <div class="stat-summary">
            <span class="pass">通过: {{ execution.passed_cases }}</span>
            <span class="fail">失败: {{ execution.failed_cases }}</span>
            <span class="error">错误: {{ execution.error_cases }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 断言 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>断言统计</template>
          <div class="assertion-stats">
            <el-statistic title="总断言" :value="execution.total_assertions" />
            <el-statistic title="失败断言" :value="execution.failed_assertions" value-style="color: #f56c6c" />
            <el-statistic title="总步骤" :value="execution.total_steps" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 报告详情 -->
    <el-card shadow="hover" style="margin-top: 20px" v-if="report">
      <template #header>步骤详情</template>
      <el-table :data="reportSteps" stripe>
        <el-table-column prop="name" label="步骤名称" min-width="200" />
        <el-table-column prop="method" label="方法" width="80" />
        <el-table-column prop="url" label="URL" min-width="250" show-overflow-tooltip />
        <el-table-column prop="status_code" label="状态码" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status_code < 400 ? 'success' : 'danger'" size="small">{{ row.status_code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="elapsed_ms" label="耗时(ms)" width="100" align="right">
          <template #default="{ row }">{{ row.elapsed_ms?.toFixed(1) }}</template>
        </el-table-column>
        <el-table-column prop="result" label="结果" width="80" align="center">
          <template #default="{ row }">
            <el-icon :color="row.passed ? '#67c23a' : '#f56c6c'">
              <component :is="row.passed ? 'CircleCheck' : 'CircleClose'" />
            </el-icon>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 日志 -->
    <el-card shadow="hover" style="margin-top: 20px" v-if="execution?.stdout || execution?.stderr">
      <template #header>执行日志</template>
      <el-tabs>
        <el-tab-pane label="stdout" v-if="execution.stdout">
          <pre class="log-output">{{ execution.stdout }}</pre>
        </el-tab-pane>
        <el-tab-pane label="stderr" v-if="execution.stderr">
          <pre class="log-output log-error">{{ execution.stderr }}</pre>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { executionApi, type Execution } from '@/api'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const route = useRoute()
const loading = ref(true)
const execution = ref<Execution | null>(null)
const report = ref<any>(null)

const statusType = computed(() => {
  switch (execution.value?.status) {
    case 'passed': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    default: return 'info'
  }
})

const resultPieOption = computed(() => {
  if (!execution.value) return {}
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['45%', '75%'],
      data: [
        { name: '通过', value: execution.value.passed_cases, itemStyle: { color: '#67c23a' } },
        { name: '失败', value: execution.value.failed_cases, itemStyle: { color: '#f56c6c' } },
        { name: '错误', value: execution.value.error_cases || 0, itemStyle: { color: '#e6a23c' } },
      ].filter(d => d.value > 0),
      label: { show: false },
    }],
  }
})

const reportSteps = computed(() => {
  if (!report.value) return []
  const steps = report.value.steps || report.value.results || []
  return steps.map((s: any) => ({
    name: s.name || s.step_name || '',
    method: s.request?.method || s.method || '',
    url: s.request?.url || s.url || '',
    status_code: s.response?.status_code || s.status_code || 0,
    elapsed_ms: s.elapsed_ms || s.duration_ms || 0,
    passed: s.passed ?? (s.status === 'passed'),
  }))
})

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    const [execRes, reportRes] = await Promise.allSettled([
      executionApi.get(id),
      executionApi.report(id),
    ])
    if (execRes.status === 'fulfilled') execution.value = execRes.value.data
    if (reportRes.status === 'fulfilled') report.value = reportRes.value.data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-summary {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 8px;
  font-size: 13px;
}
.stat-summary .pass { color: #67c23a; }
.stat-summary .fail { color: #f56c6c; }
.stat-summary .error { color: #e6a23c; }

.assertion-stats {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
}

.log-output {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-error { color: #f56c6c; }
</style>
