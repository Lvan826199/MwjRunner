<template>
  <div class="pipelines-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openCreate">新建 Pipeline</el-button>
      <el-button :icon="Refresh" @click="loadList">刷新</el-button>
    </div>

    <!-- Pipeline 卡片网格 -->
    <div class="pipeline-grid" v-loading="loading">
      <div v-for="p in pipelines" :key="p.id" class="pipeline-card" :class="`pipeline-card--${p.last_status}`">
        <div class="pipeline-card__header">
          <div class="pipeline-card__status">
            <span class="status-dot" :class="`dot--${p.last_status}`" />
            <span class="status-text">{{ statusLabel(p.last_status) }}</span>
          </div>
          <div class="pipeline-card__actions">
            <el-button size="small" text type="primary" :icon="CaretRight" @click="triggerPipeline(p)" :disabled="!p.is_active">
              触发
            </el-button>
            <el-button size="small" text :icon="Edit" @click="openEdit(p)" />
            <el-popconfirm title="确定删除？" @confirm="handleDelete(p.id)">
              <template #reference>
                <el-button size="small" text type="danger" :icon="Delete" />
              </template>
            </el-popconfirm>
          </div>
        </div>

        <div class="pipeline-card__body">
          <div class="pipeline-card__name">{{ p.name }}</div>
          <div class="pipeline-card__meta">
            <el-tag size="small" effect="plain">{{ platformLabel(p.platform) }}</el-tag>
            <el-tag size="small" effect="plain" type="info">{{ triggerLabel(p.trigger_type) }}</el-tag>
            <el-tag v-if="p.case_filter_tags" size="small" effect="plain" type="warning">{{ p.case_filter_tags }}</el-tag>
          </div>
        </div>

        <div class="pipeline-card__footer">
          <span class="last-run" v-if="p.last_run_at">上次运行: {{ formatTime(p.last_run_at) }}</span>
          <span class="last-run" v-else>尚未运行</span>
          <el-button size="small" text @click="openRuns(p)">历史记录</el-button>
        </div>
      </div>

      <div v-if="!loading && pipelines.length === 0" class="pipeline-empty">
        <el-empty description="暂无 Pipeline 配置" />
      </div>
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="editId ? '编辑 Pipeline' : '新建 Pipeline'" width="560px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如：主分支回归测试" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="CI 平台">
              <el-select v-model="form.platform" style="width: 100%">
                <el-option label="GitHub Actions" value="github" />
                <el-option label="GitLab CI" value="gitlab" />
                <el-option label="Jenkins" value="jenkins" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="触发方式">
              <el-select v-model="form.trigger_type" style="width: 100%">
                <el-option label="Webhook" value="webhook" />
                <el-option label="定时" value="schedule" />
                <el-option label="手动" value="manual" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="form.trigger_type === 'schedule'" label="Cron 表达式">
          <el-input v-model="form.cron_expr" placeholder="0 2 * * *" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="用例标签筛选">
              <el-input v-model="form.case_filter_tags" placeholder="smoke,regression" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="环境名称">
              <el-input v-model="form.env_name" placeholder="staging" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="http://api.staging.example.com" />
        </el-form-item>
        <el-form-item label="失败通知 Webhook">
          <el-input v-model="form.notify_webhook" placeholder="钉钉/飞书/Slack Webhook URL" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 执行记录抽屉 -->
    <el-drawer v-model="showRuns" :title="`${currentPipeline?.name} - 执行记录`" size="500px">
      <el-table :data="runs" v-loading="loadingRuns" stripe size="small">
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="runStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_source" label="触发" width="80" />
        <el-table-column prop="branch" label="分支" width="100" show-overflow-tooltip />
        <el-table-column label="结果" width="120">
          <template #default="{ row }">
            <span v-if="row.total_cases">{{ row.passed_cases }}/{{ row.total_cases }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="140">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Refresh, Edit, Delete, CaretRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { pipelineApi, type Pipeline, type PipelineRun } from '../api'

const pipelines = ref<Pipeline[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editId = ref<number | null>(null)
const showRuns = ref(false)
const loadingRuns = ref(false)
const runs = ref<PipelineRun[]>([])
const currentPipeline = ref<Pipeline | null>(null)

const form = ref({
  name: '',
  platform: 'github',
  trigger_type: 'webhook',
  cron_expr: '',
  case_filter_tags: '',
  env_name: '',
  base_url: '',
  notify_webhook: '',
  description: '',
})

onMounted(() => loadList())

async function loadList() {
  loading.value = true
  try {
    const { data } = await pipelineApi.list()
    pipelines.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editId.value = null
  Object.assign(form.value, { name: '', platform: 'github', trigger_type: 'webhook', cron_expr: '', case_filter_tags: '', env_name: '', base_url: '', notify_webhook: '', description: '' })
  showDialog.value = true
}

function openEdit(p: Pipeline) {
  editId.value = p.id
  Object.assign(form.value, { name: p.name, platform: p.platform, trigger_type: p.trigger_type, cron_expr: p.cron_expr, case_filter_tags: p.case_filter_tags, env_name: p.env_name, base_url: p.base_url, notify_webhook: p.notify_webhook, description: p.description })
  showDialog.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editId.value) {
      await pipelineApi.update(editId.value, form.value)
      ElMessage.success('已更新')
    } else {
      await pipelineApi.create(form.value)
      ElMessage.success('已创建')
    }
    showDialog.value = false
    loadList()
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  await pipelineApi.delete(id)
  ElMessage.success('已删除')
  loadList()
}

async function triggerPipeline(p: Pipeline) {
  await pipelineApi.trigger(p.id, { trigger_source: 'manual' })
  ElMessage.success('已触发')
  loadList()
}

async function openRuns(p: Pipeline) {
  currentPipeline.value = p
  showRuns.value = true
  loadingRuns.value = true
  try {
    const { data } = await pipelineApi.runs(p.id)
    runs.value = data
  } finally {
    loadingRuns.value = false
  }
}

function statusLabel(s: string) {
  const map: Record<string, string> = { passing: '通过', failing: '失败', unknown: '未知' }
  return map[s] || s
}

function platformLabel(s: string) {
  const map: Record<string, string> = { github: 'GitHub', gitlab: 'GitLab', jenkins: 'Jenkins', custom: '自定义' }
  return map[s] || s
}

function triggerLabel(s: string) {
  const map: Record<string, string> = { webhook: 'Webhook', schedule: '定时', manual: '手动' }
  return map[s] || s
}

function runStatusType(s: string) {
  const map: Record<string, string> = { passed: 'success', failed: 'danger', running: 'warning', pending: 'info' }
  return (map[s] || 'info') as any
}

function formatTime(t: string | null) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style scoped>
.pipelines-page { padding: 0; }

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pipeline-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.pipeline-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #ebeef5;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s;
}
.pipeline-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.pipeline-card--passing { border-left: 3px solid #67c23a; }
.pipeline-card--failing { border-left: 3px solid #f56c6c; }
.pipeline-card--unknown { border-left: 3px solid #909399; }

.pipeline-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.pipeline-card__status {
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot--passing { background: #67c23a; }
.dot--failing { background: #f56c6c; }
.dot--unknown { background: #909399; }
.status-text { font-size: 12px; color: #606266; }

.pipeline-card__actions {
  display: flex;
  gap: 2px;
}

.pipeline-card__body { margin-bottom: 12px; }
.pipeline-card__name {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}
.pipeline-card__meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pipeline-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f5f5f5;
  padding-top: 8px;
}
.last-run {
  font-size: 12px;
  color: #909399;
}
</style>
