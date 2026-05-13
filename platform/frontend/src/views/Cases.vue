<template>
  <el-container class="cases-container">
    <!-- 左侧目录树 -->
    <el-aside width="240px" class="folder-aside">
      <div class="folder-header">
        <span>用例目录</span>
        <el-button :icon="FolderAdd" size="small" text @click="createFolder" />
      </div>
      <el-tree
        :data="folderTree"
        node-key="path"
        default-expand-all
        highlight-current
        @node-click="handleFolderClick"
      >
        <template #default="{ node, data }">
          <span class="folder-node">
            <el-icon><Folder /></el-icon>
            <span>{{ data.label }}</span>
          </span>
        </template>
      </el-tree>
      <div v-if="folderTree.length === 0" class="folder-empty">
        <el-text type="info" size="small">暂无目录</el-text>
      </div>
    </el-aside>

    <!-- 右侧主内容 -->
    <el-main class="cases-main">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-input
          v-model="searchText"
          placeholder="搜索用例名称"
          :prefix-icon="Search"
          clearable
          style="width: 240px"
          @input="handleSearch"
        />
        <el-select v-model="filterTag" placeholder="标签筛选" clearable style="width: 140px" @change="loadCases">
          <el-option label="smoke" value="smoke" />
          <el-option label="auth" value="auth" />
          <el-option label="regression" value="regression" />
        </el-select>
        <el-select v-model="filterPriority" placeholder="优先级" clearable style="width: 120px" @change="loadCases">
          <el-option label="P0" value="P0" />
          <el-option label="P1" value="P1" />
          <el-option label="P2" value="P2" />
          <el-option label="P3" value="P3" />
        </el-select>
        <div class="toolbar-right">
          <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">新建用例</el-button>
          <el-dropdown @command="handleImport">
            <el-button :icon="Upload">导入</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="postman">从 Postman 导入</el-dropdown-item>
                <el-dropdown-item command="openapi">从 OpenAPI 导入</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- 用例表格 -->
      <el-table :data="cases" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="用例名称" min-width="200" />
        <el-table-column prop="tags" label="标签" width="150">
          <template #default="{ row }">
            <el-tag v-for="tag in parseTags(row.tags)" :key="tag" size="small" style="margin-right: 4px">
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="dark">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_at" label="最近执行" width="160">
          <template #default="{ row }">
            {{ row.last_run_at ? formatTime(row.last_run_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="editCase(row)">编辑</el-button>
            <el-button size="small" text type="success" @click="runCase(row)">执行</el-button>
            <el-popconfirm title="确定删除该用例？" @confirm="deleteCase(row.id)">
              <template #reference>
                <el-button size="small" text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-main>

    <!-- 新建用例对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建用例" width="500px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="用例名称">
          <el-input v-model="createForm.name" placeholder="请输入用例名称" />
        </el-form-item>
        <el-form-item label="所属目录">
          <el-input v-model="createForm.folder" placeholder="/" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="createForm.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority" style="width: 100%">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search, Plus, Upload, Folder, FolderAdd } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { caseApi, type TestCase, type FolderNode } from '../api'

const cases = ref<TestCase[]>([])
const folderTree = ref<FolderNode[]>([])
const loading = ref(false)
const searchText = ref('')
const filterTag = ref('')
const filterPriority = ref('')
const currentFolder = ref('')
const showCreateDialog = ref(false)
const createForm = ref({ name: '', folder: '/', tags: '', priority: 'P2' })

onMounted(() => {
  loadCases()
  loadFolders()
})

async function loadCases() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (currentFolder.value) params.folder = currentFolder.value
    if (filterTag.value) params.tags = filterTag.value
    if (filterPriority.value) params.priority = filterPriority.value
    if (searchText.value) params.search = searchText.value
    const { data } = await caseApi.list(params)
    cases.value = data
  } finally {
    loading.value = false
  }
}

async function loadFolders() {
  const { data } = await caseApi.folders()
  folderTree.value = data
}

function handleFolderClick(data: FolderNode) {
  currentFolder.value = data.path
  loadCases()
}

function handleSearch() {
  loadCases()
}

async function handleCreate() {
  if (!createForm.value.name) {
    ElMessage.warning('请输入用例名称')
    return
  }
  await caseApi.create(createForm.value)
  ElMessage.success('用例创建成功')
  showCreateDialog.value = false
  createForm.value = { name: '', folder: '/', tags: '', priority: 'P2' }
  loadCases()
  loadFolders()
}

async function deleteCase(id: number) {
  await caseApi.delete(id)
  ElMessage.success('删除成功')
  loadCases()
}

function editCase(row: TestCase) {
  ElMessage.info('编辑功能开发中')
}

function runCase(row: TestCase) {
  ElMessage.info('执行功能开发中')
}

function handleImport(command: string) {
  ElMessage.info(`${command} 导入功能开发中`)
}

function createFolder() {
  ElMessage.info('新建目录功能开发中')
}

function parseTags(tags: string): string[] {
  return tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : []
}

function priorityType(p: string) {
  if (p === 'P0') return 'danger'
  if (p === 'P1') return 'warning'
  if (p === 'P2') return 'info'
  return ''
}

function statusType(s: string) {
  if (s === 'passed') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'error') return 'warning'
  return 'info'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { idle: '未执行', passed: '通过', failed: '失败', error: '错误' }
  return map[s] || s
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style scoped>
.cases-container {
  height: 100%;
}
.folder-aside {
  background: #fafafa;
  border-right: 1px solid #eee;
  padding: 12px 0;
}
.folder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px 12px;
  font-weight: 500;
}
.folder-node {
  display: flex;
  align-items: center;
  gap: 6px;
}
.folder-empty {
  padding: 20px;
  text-align: center;
}
.cases-main {
  padding: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.toolbar-right {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
</style>
