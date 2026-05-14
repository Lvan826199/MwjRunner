<template>
  <div class="users-page">
    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="用户管理" name="users" />
      <el-tab-pane label="团队管理" name="teams" />
    </el-tabs>

    <!-- 用户管理 -->
    <div v-show="activeTab === 'users'">
      <div class="toolbar">
        <el-input v-model="userSearch" placeholder="搜索用户名" :prefix-icon="Search" clearable style="width: 200px" />
        <div style="flex: 1" />
        <el-button type="primary" :icon="Plus" @click="openCreateUser">新建用户</el-button>
      </div>

      <el-table :data="filteredUsers" v-loading="loadingUsers" stripe>
        <el-table-column label="状态" width="60" align="center">
          <template #default="{ row }">
            <span class="status-dot" :class="row.is_active ? 'dot--active' : 'dot--inactive'" />
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="display_name" label="显示名" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="团队" width="120">
          <template #default="{ row }">
            {{ teamName(row.team_id) }}
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="160">
          <template #default="{ row }">{{ row.last_login_at ? formatTime(row.last_login_at) : '从未' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text :icon="Edit" @click="openEditUser(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDeleteUser(row.id)">
              <template #reference>
                <el-button size="small" text type="danger" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 团队管理 -->
    <div v-show="activeTab === 'teams'">
      <div class="toolbar">
        <div style="flex: 1" />
        <el-button type="primary" :icon="Plus" @click="openCreateTeam">新建团队</el-button>
      </div>

      <div class="team-grid">
        <div v-for="t in teams" :key="t.id" class="team-card">
          <div class="team-card__header">
            <span class="team-card__name">{{ t.name }}</span>
            <div>
              <el-button size="small" text :icon="Edit" @click="openEditTeam(t)" />
              <el-popconfirm title="确定删除？" @confirm="handleDeleteTeam(t.id)">
                <template #reference>
                  <el-button size="small" text type="danger" :icon="Delete" />
                </template>
              </el-popconfirm>
            </div>
          </div>
          <div class="team-card__desc">{{ t.description || '暂无描述' }}</div>
          <div class="team-card__meta">
            <span>成员上限: {{ t.max_members }}</span>
            <span>当前成员: {{ teamMemberCount(t.id) }}</span>
          </div>
        </div>
        <div v-if="teams.length === 0" style="grid-column: 1/-1">
          <el-empty description="暂无团队" />
        </div>
      </div>
    </div>

    <!-- 用户对话框 -->
    <el-dialog v-model="showUserDialog" :title="editUserId ? '编辑用户' : '新建用户'" width="440px">
      <el-form :model="userForm" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="userForm.username" :disabled="!!editUserId" />
        </el-form-item>
        <el-form-item v-if="!editUserId" label="密码">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="userForm.display_name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="角色">
              <el-select v-model="userForm.role" style="width: 100%">
                <el-option label="管理员" value="admin" />
                <el-option label="经理" value="manager" />
                <el-option label="成员" value="member" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="团队">
              <el-select v-model="userForm.team_id" clearable placeholder="无" style="width: 100%">
                <el-option v-for="t in teams" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="showUserDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveUser" :loading="savingUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 团队对话框 -->
    <el-dialog v-model="showTeamDialog" :title="editTeamId ? '编辑团队' : '新建团队'" width="400px">
      <el-form :model="teamForm" label-position="top">
        <el-form-item label="团队名称">
          <el-input v-model="teamForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="teamForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="成员上限">
          <el-input-number v-model="teamForm.max_members" :min="1" :max="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTeamDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveTeam" :loading="savingTeam">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { userApi, teamApi, type UserInfo, type TeamInfo } from '../api'

const activeTab = ref('users')
const loadingUsers = ref(false)
const users = ref<UserInfo[]>([])
const teams = ref<TeamInfo[]>([])
const userSearch = ref('')

const filteredUsers = computed(() => {
  if (!userSearch.value) return users.value
  const q = userSearch.value.toLowerCase()
  return users.value.filter(u => u.username.toLowerCase().includes(q) || u.display_name.toLowerCase().includes(q))
})

// 用户表单
const showUserDialog = ref(false)
const editUserId = ref<number | null>(null)
const savingUser = ref(false)
const userForm = ref({ username: '', password: '', display_name: '', email: '', role: 'member', team_id: undefined as number | undefined })

// 团队表单
const showTeamDialog = ref(false)
const editTeamId = ref<number | null>(null)
const savingTeam = ref(false)
const teamForm = ref({ name: '', description: '', max_members: 50 })

function roleType(role: string) {
  return role === 'admin' ? 'danger' : role === 'manager' ? 'warning' : 'info'
}
function roleLabel(role: string) {
  return role === 'admin' ? '管理员' : role === 'manager' ? '经理' : '成员'
}
function teamName(teamId: number | null) {
  if (!teamId) return '-'
  return teams.value.find(t => t.id === teamId)?.name || '-'
}
function teamMemberCount(teamId: number) {
  return users.value.filter(u => u.team_id === teamId).length
}
function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const { data } = await userApi.list()
    users.value = data
  } finally {
    loadingUsers.value = false
  }
}
async function loadTeams() {
  const { data } = await teamApi.list()
  teams.value = data
}
function handleTabChange() {
  if (activeTab.value === 'teams') loadTeams()
}

function openCreateUser() {
  editUserId.value = null
  userForm.value = { username: '', password: '', display_name: '', email: '', role: 'member', team_id: undefined }
  showUserDialog.value = true
}
function openEditUser(u: UserInfo) {
  editUserId.value = u.id
  userForm.value = { username: u.username, password: '', display_name: u.display_name, email: u.email, role: u.role, team_id: u.team_id || undefined }
  showUserDialog.value = true
}
async function handleSaveUser() {
  savingUser.value = true
  try {
    if (editUserId.value) {
      await userApi.update(editUserId.value, { display_name: userForm.value.display_name, email: userForm.value.email, role: userForm.value.role, team_id: userForm.value.team_id as any })
    } else {
      await userApi.create(userForm.value as any)
    }
    ElMessage.success('保存成功')
    showUserDialog.value = false
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingUser.value = false
  }
}
async function handleDeleteUser(id: number) {
  await userApi.delete(id)
  ElMessage.success('已删除')
  await loadUsers()
}

function openCreateTeam() {
  editTeamId.value = null
  teamForm.value = { name: '', description: '', max_members: 50 }
  showTeamDialog.value = true
}
function openEditTeam(t: TeamInfo) {
  editTeamId.value = t.id
  teamForm.value = { name: t.name, description: t.description, max_members: t.max_members }
  showTeamDialog.value = true
}
async function handleSaveTeam() {
  savingTeam.value = true
  try {
    if (editTeamId.value) {
      await teamApi.update(editTeamId.value, teamForm.value)
    } else {
      await teamApi.create(teamForm.value)
    }
    ElMessage.success('保存成功')
    showTeamDialog.value = false
    await loadTeams()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingTeam.value = false
  }
}
async function handleDeleteTeam(id: number) {
  await teamApi.delete(id)
  ElMessage.success('已删除')
  await loadTeams()
}

onMounted(() => {
  loadUsers()
  loadTeams()
})
</script>

<style scoped>
.users-page { padding: 20px; }
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.dot--active { background: #67c23a; }
.dot--inactive { background: #909399; }

.team-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.team-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  transition: box-shadow 0.2s;
}
.team-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.team-card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.team-card__name { font-weight: 600; font-size: 15px; }
.team-card__desc { color: #909399; font-size: 13px; margin-bottom: 12px; }
.team-card__meta { display: flex; gap: 16px; font-size: 12px; color: #606266; }
</style>
