<template>
  <div class="env-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchText"
        placeholder="搜索环境名称"
        :prefix-icon="Search"
        clearable
        style="width: 220px"
      />
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建环境</el-button>
    </div>

    <!-- 环境卡片网格 -->
    <div class="env-grid" v-loading="loading">
      <div
        v-for="env in filteredEnvs"
        :key="env.id"
        class="env-card"
        :class="{ 'env-card--inactive': !env.is_active }"
        @click="openDetail(env)"
      >
        <div class="env-card__header">
          <div class="env-card__title">
            <span class="env-card__dot" :class="env.is_active ? 'dot--active' : 'dot--inactive'" />
            <span class="env-card__name">{{ env.name }}</span>
          </div>
          <el-tag v-if="env.auth_type" size="small" type="info" effect="plain">
            {{ authLabel(env.auth_type) }}
          </el-tag>
        </div>
        <div class="env-card__body">
          <div class="env-card__url" :title="env.base_url">
            {{ env.base_url || '未配置 base_url' }}
          </div>
          <div class="env-card__label">{{ env.label }}</div>
        </div>
        <div class="env-card__footer">
          <el-button size="small" text :icon="Edit" @click.stop="openEdit(env)">编辑</el-button>
          <el-button size="small" text :icon="CopyDocument" @click.stop="handleClone(env)">克隆</el-button>
          <el-button
            size="small"
            text
            :icon="env.is_active ? Close : Check"
            @click.stop="toggleActive(env)"
          >
            {{ env.is_active ? '停用' : '启用' }}
          </el-button>
          <el-popconfirm title="确定删除该环境？" @confirm="handleDelete(env.id)">
            <template #reference>
              <el-button size="small" text type="danger" :icon="Delete" @click.stop>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && filteredEnvs.length === 0" class="env-empty">
        <el-empty description="暂无环境配置，点击上方按钮创建" />
      </div>
    </div>

    <!-- 详情/编辑抽屉 -->
    <el-drawer v-model="showDrawer" :title="drawerTitle" size="520px" @close="resetForm">
      <el-form :model="form" label-width="90px" label-position="top">
        <el-form-item label="环境名称">
          <el-input v-model="form.name" placeholder="如 dev / test / prod" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.label" placeholder="如 开发环境" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="http://api.example.com" />
        </el-form-item>
        <el-form-item label="超时时间(秒)">
          <el-input-number v-model="form.timeout" :min="1" :max="600" />
        </el-form-item>

        <el-divider content-position="left">认证配置</el-divider>
        <el-form-item label="认证类型">
          <el-select v-model="form.auth_type" clearable placeholder="无认证" style="width: 100%">
            <el-option label="Bearer Token" value="bearer" />
            <el-option label="Basic Auth" value="basic" />
            <el-option label="OAuth2" value="oauth2" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.auth_type === 'bearer'" label="Token">
          <el-input v-model="form.auth_token" type="password" show-password placeholder="Bearer Token" />
        </el-form-item>
        <el-form-item v-if="form.auth_type === 'basic'" label="用户名">
          <el-input v-model="form.auth_username" placeholder="用户名" />
        </el-form-item>
        <el-form-item v-if="form.auth_type === 'basic'" label="密码">
          <el-input v-model="form.auth_password" type="password" show-password placeholder="密码" />
        </el-form-item>

        <el-divider content-position="left">全局 Headers</el-divider>
        <el-form-item>
          <el-input
            v-model="form.headers"
            type="textarea"
            :rows="4"
            placeholder='{"Content-Type": "application/json"}'
          />
        </el-form-item>

        <el-divider content-position="left">全局变量</el-divider>
        <el-form-item>
          <el-input
            v-model="form.variables"
            type="textarea"
            :rows="4"
            placeholder='{"env": "dev", "api_version": "v1"}'
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="环境描述" />
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
import { Search, Plus, Edit, Delete, CopyDocument, Close, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { environmentApi, type Environment } from '../api'

const environments = ref<Environment[]>([])
const loading = ref(false)
const saving = ref(false)
const searchText = ref('')
const showDrawer = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

const form = ref({
  name: '',
  label: '',
  base_url: '',
  timeout: 30,
  auth_type: '',
  auth_token: '',
  auth_username: '',
  auth_password: '',
  headers: '{}',
  variables: '{}',
  description: '',
})

const filteredEnvs = computed(() => {
  if (!searchText.value) return environments.value
  const q = searchText.value.toLowerCase()
  return environments.value.filter(
    e => e.name.toLowerCase().includes(q) || e.label.toLowerCase().includes(q)
  )
})

const drawerTitle = computed(() => isEdit.value ? '编辑环境' : '新建环境')

onMounted(() => loadEnvironments())

async function loadEnvironments() {
  loading.value = true
  try {
    const { data } = await environmentApi.list()
    environments.value = data
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  editId.value = null
  resetForm()
  showDrawer.value = true
}

function openEdit(env: Environment) {
  isEdit.value = true
  editId.value = env.id
  form.value = {
    name: env.name,
    label: env.label,
    base_url: env.base_url,
    timeout: env.timeout,
    auth_type: env.auth_type,
    auth_token: env.auth_token,
    auth_username: env.auth_username,
    auth_password: env.auth_password,
    headers: env.headers,
    variables: env.variables,
    description: env.description,
  }
  showDrawer.value = true
}

function openDetail(env: Environment) {
  openEdit(env)
}

async function handleSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入环境名称')
    return
  }
  saving.value = true
  try {
    if (isEdit.value && editId.value) {
      await environmentApi.update(editId.value, form.value)
      ElMessage.success('环境更新成功')
    } else {
      await environmentApi.create(form.value)
      ElMessage.success('环境创建成功')
    }
    showDrawer.value = false
    await loadEnvironments()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  await environmentApi.delete(id)
  ElMessage.success('环境已删除')
  await loadEnvironments()
}

async function handleClone(env: Environment) {
  const newName = `${env.name}_copy`
  try {
    await environmentApi.clone(env.id, newName)
    ElMessage.success(`已克隆为 ${newName}`)
    await loadEnvironments()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '克隆失败')
  }
}

async function toggleActive(env: Environment) {
  await environmentApi.update(env.id, { is_active: env.is_active ? 0 : 1 } as any)
  ElMessage.success(env.is_active ? '已停用' : '已启用')
  await loadEnvironments()
}

function resetForm() {
  form.value = {
    name: '', label: '', base_url: '', timeout: 30,
    auth_type: '', auth_token: '', auth_username: '', auth_password: '',
    headers: '{}', variables: '{}', description: '',
  }
}

function authLabel(type: string) {
  const map: Record<string, string> = { bearer: 'Bearer', basic: 'Basic', oauth2: 'OAuth2' }
  return map[type] || type
}
</script>

<style scoped>
.env-page {
  padding: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.env-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.env-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.env-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.env-card--inactive {
  opacity: 0.6;
  background: #fafafa;
}

.env-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.env-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.env-card__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot--active {
  background: #67c23a;
  box-shadow: 0 0 4px rgba(103, 194, 58, 0.4);
}

.dot--inactive {
  background: #c0c4cc;
}

.env-card__name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.env-card__body {
  margin-bottom: 12px;
}

.env-card__url {
  font-size: 13px;
  color: #606266;
  font-family: 'Fira Code', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.env-card__label {
  font-size: 12px;
  color: #909399;
}

.env-card__footer {
  display: flex;
  gap: 4px;
  border-top: 1px solid #f2f3f5;
  padding-top: 10px;
}

.env-empty {
  grid-column: 1 / -1;
}
</style>
