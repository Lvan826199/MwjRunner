<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #ecf5ff"><el-icon :size="28" color="#409eff"><Document /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ overview.cases?.total ?? 0 }}</div>
            <div class="stat-label">用例总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #f0f9eb"><el-icon :size="28" color="#67c23a"><VideoPlay /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ overview.executions?.today ?? 0 }}</div>
            <div class="stat-label">今日执行</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fdf6ec"><el-icon :size="28" color="#e6a23c"><TrendCharts /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ passRateText }}</div>
            <div class="stat-label">通过率 ({{ days }}天)</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fef0f0"><el-icon :size="28" color="#f56c6c"><Setting /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ overview.environments?.total ?? 0 }}</div>
            <div class="stat-label">环境数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="chart-header">
              <span>执行趋势</span>
              <el-radio-group v-model="days" size="small" @change="fetchData">
                <el-radio-button :value="7">7天</el-radio-button>
                <el-radio-button :value="14">14天</el-radio-button>
                <el-radio-button :value="30">30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="trendOption" style="height: 320px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>用例状态分布</template>
          <v-chart :option="statusPieOption" style="height: 320px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>优先级分布</template>
          <v-chart :option="priorityBarOption" style="height: 260px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>标签 Top 10</template>
          <v-chart :option="tagBarOption" style="height: 260px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { statsApi } from '@/api'

use([CanvasRenderer, LineChart, PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const days = ref(7)
const overview = ref<any>({})
const trend = ref<any[]>([])
const tags = ref<any[]>([])

const passRateText = computed(() => {
  const rate = overview.value.executions?.pass_rate
  if (rate === undefined || rate === null) return '-'
  return `${(rate * 100).toFixed(1)}%`
})

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['通过', '失败', '通过率'] },
  grid: { left: 50, right: 50, bottom: 30, top: 40 },
  xAxis: { type: 'category', data: trend.value.map(t => t.date) },
  yAxis: [
    { type: 'value', name: '次数' },
    { type: 'value', name: '通过率', max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
  ],
  series: [
    { name: '通过', type: 'line', data: trend.value.map(t => t.passed), smooth: true, itemStyle: { color: '#67c23a' } },
    { name: '失败', type: 'line', data: trend.value.map(t => t.failed), smooth: true, itemStyle: { color: '#f56c6c' } },
    { name: '通过率', type: 'line', yAxisIndex: 1, data: trend.value.map(t => t.pass_rate), smooth: true, lineStyle: { type: 'dashed' }, itemStyle: { color: '#e6a23c' } },
  ],
}))

const statusPieOption = computed(() => {
  const byStatus = overview.value.cases?.by_status || {}
  const colorMap: Record<string, string> = { passed: '#67c23a', failed: '#f56c6c', idle: '#909399', error: '#e6a23c' }
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: Object.entries(byStatus).map(([name, value]) => ({
        name, value, itemStyle: { color: colorMap[name] || '#409eff' },
      })),
      label: { formatter: '{b}: {c}' },
    }],
  }
})

const priorityBarOption = computed(() => {
  const byPriority = overview.value.cases?.by_priority || {}
  const priorities = ['P0', 'P1', 'P2', 'P3']
  const colorMap: Record<string, string> = { P0: '#f56c6c', P1: '#e6a23c', P2: '#409eff', P3: '#909399' }
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, bottom: 30, top: 20 },
    xAxis: { type: 'category', data: priorities },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: priorities.map(p => ({ value: byPriority[p] || 0, itemStyle: { color: colorMap[p] } })),
      barWidth: '50%',
    }],
  }
})

const tagBarOption = computed(() => {
  const top10 = tags.value.slice(0, 10)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 20, bottom: 30, top: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: top10.map(t => t.name).reverse() },
    series: [{
      type: 'bar',
      data: top10.map(t => t.count).reverse(),
      itemStyle: { color: '#409eff' },
    }],
  }
})

async function fetchData() {
  try {
    const [overviewRes, trendRes, tagsRes] = await Promise.all([
      statsApi.overview(days.value),
      statsApi.trend(days.value),
      statsApi.tags(),
    ])
    overview.value = overviewRes.data
    trend.value = trendRes.data.trend || []
    tags.value = tagsRes.data.tags || []
  } catch { /* ignore on first load */ }
}

onMounted(fetchData)
</script>

<style scoped>
.stat-row {
  margin-bottom: 0;
}
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}
.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-info {
  flex: 1;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
