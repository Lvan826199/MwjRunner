<template>
  <div class="mocks-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input v-model="searchText" placeholder="搜索规则名称或路径" :prefix-icon="Search" clearable style="width: 240px" />
      <el-select v-model="filterMethod" clearable placeholder="HTTP 方法" style="width: 120px">
        <el-option label="GET" value="GET" />
        <el-option label="POST" value="POST" />
        <el-option label="PUT" value="PUT" />
        <el-option label="DELETE" value="DELETE" />
        <el-option label="PATCH" value="PATCH" />
      </el-select>
      <div style="flex: 1" />
      <el-button type="primary" :icon="Plus" @click="openCreate">新建规则</el-button>
    </div>

    <!-- Mock 规则表格 -->
    <el-table :data="filteredRules" v-loading="loading" stripe style="width: 100%" row-class-name="mock-row">
      <el-table-column label="状态" width="60" align="center">
        <template #default="{ row }">
          <span class="status-dot" :class="row.is_active ? 'dot--active' : 'dot--inactive'" />
        </template>
      </el-table-column>
      <el-table-column label="方法" width="80">
        <template #default="{ row }">
          <el-tag :type="methodTagType(row.method)" size="small" effect="dark">{{ row.method }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
      <el-table-column prop="name" label="规则名称" min-width="160" show-overflow-tooltip />
      <el-table-column label="响应码" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.response_status >= 400 ? 'danger' : 'success'" size="small" effect="plain">
            {{ row.response_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="延迟" width="70" align="center">
        <template #default="{ row }">
          {{ row.response_delay_ms ? `${row.response_delay_ms}ms` : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="命中" width="70" align="center">
        <template #default="{ row }">
          <span class="hit-count">{{ row.hit_count }}</span>
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="70" align="center" prop="priority" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" text @click="toggleActive(row)">
            {{ row.is_active ? '停用' : '启用' }}
          </el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" text type="danger" :icon="Delete">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/编辑抽屉 -->
    <el-drawer v-model="showDrawer" :title="drawerTitle" size="560px" @close="resetForm">
      <el-form :model="form" label-position="top">
        <el-form-item label="规则名称">
          <el-input v-model="form.name" placeholder="如：获取用户列表" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="HTTP 方法">
              <el-select v-model="form.method" style="width: 100%">
                <el-option v-for="m in ['GET','POST','PUT','DELETE','PATCH']" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="路径">
              <el-input v-model="form.path" placeholder="/api/users/:id" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">响应配置</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="状态码">
              <el-input-number v-model="form.response_status" :min="100" :max="599" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="延迟(ms)">
              <el-input-number v-model="form.response_delay_ms" :min="0" :max="30000" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="0" :max="100" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="响应 Headers">
          <el-input v-model="form.response_headers" type="textarea" :rows="2" placeholder='{"Content-Type": "application/json"}' />
        </el-form-item>
        <el-form-item label="响应 Body">
          <el-input v-model="form.response_body" type="textarea" :rows="6" placeholder='{"id": 1, "name": "mock user"}' />
        </el-form-item>

        <el-divider content-position="left">请求匹配（可选）</el-divider>
        <el-form-item label="匹配 Headers">
          <el-input v-model="form.match_headers" type="textarea" :rows="2" placeholder='{"Authorization": "Bearer *"}' />
        </el-form-item>
        <el-form-item label="匹配 Query">
          <el-input v-model="form.match_query" type="textarea" :rows="2" placeholder='{"page": "1"}' />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDrawer = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { mockApi, type MockRule } from '../api'

const rules = ref<MockRule[]>([])
const loading = ref(false)
const saving = ref(false)
const searchText = ref('')
const filterMethod = ref('')
const showDrawer = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

const form = ref({
  name: '',
  method: 'GET',
  path: '',
  match_headers: '{}',
  match_query: '{}',
  match_body: '',
  response_status: 200,
  response_headers: '{"Content-Type": "application/json"}',
  response_body: '{}',
  response_delay_ms: 0,
  priority: 0,
  description: '',
})

const filteredRules = computed(() => {
  let list = rules.value
  if (filterMethod.value) {
    list = list.filter(r => r.method === filterMethod.value)
  }
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(r => r.name.toLowerCase().includes(q) || r.path.toLowerCase().includes(q))
  }
  return list
})

const drawerTitle = computed(() => isEdit.value ? '编辑 Mock 规则' : '新建 Mock 规则')

onMounted(() => loadRules())

async function loadRules() {
  loading.value = true
  try {
    const { data } = await mockApi.list()
    rules.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  resetForm()
  showDrawer.value = true
}

function openEdit(rule: MockRule) {
  isEdit.value = true
  editId.value = rule.id
  form.value = {
    name: rule.name,
    method: rule.method,
    path: rule.path,
    match_headers: rule.match_headers,
    match_query: rule.match_query,
    match_body: rule.match_body,
    response_status: rule.response_status,
    response_headers: rule.response_headers,
    response_body: rule.response_body,
    response_delay_ms: rule.response_delay_ms,
    priority: rule.priority,
    description: rule.description,
  }
  showDrawer.value = true
}

async function handleSave() {
  if (!form.value.name || !form.value.path) {
    ElMessage.warning('请填写规则名称和路径')
    return
  }
  saving.value = true
  try {
    if (isEdit.value && editId.value) {
      await mockApi.update(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await mockApi.create(form.value as any)
      ElMessage.success('创建成功')
    }
    showDrawer.value = false
    loadRules()
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  await mockApi.delete(id)
  ElMessage.success('已删除')
  loadRules()
}

async function toggleActive(rule: MockRule) {
  await mockApi.update(rule.id, { is_active: rule.is_active ? 0 : 1 } as any)
  loadRules()
}

function resetForm() {
  form.value = {
    name: '', method: 'GET', path: '',
    match_headers: '{}', match_query: '{}', match_body: '',
    response_status: 200, response_headers: '{"Content-Type": "application/json"}',
    response_body: '{}', response_delay_ms: 0, priority: 0, description: '',
  }
}

function methodTagType(method: string) {
  const map: Record<string, string> = {
    GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info',
  }
  return (map[method] || '') as any
}
</script>

<style scoped>
.mocks-page {
  padding: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot--active { background: #67c23a; }
.dot--inactive { background: #c0c4cc; }
.hit-count {
  font-weight: 600;
  color: #409eff;
}
.mock-row {
  cursor: pointer;
}
</style>
