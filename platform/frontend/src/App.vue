<template>
  <el-container class="app-container" v-if="route.path === '/login'">
    <router-view />
  </el-container>
  <el-container class="app-container" v-else>
    <el-aside width="220px" class="app-aside">
      <div class="logo">
        <h2>MwjRunner</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/cases">
          <el-icon><Document /></el-icon>
          <span>用例管理</span>
        </el-menu-item>
        <el-menu-item index="/executions">
          <el-icon><VideoPlay /></el-icon>
          <span>执行记录</span>
        </el-menu-item>
        <el-menu-item index="/environments">
          <el-icon><Setting /></el-icon>
          <span>环境配置</span>
        </el-menu-item>
        <el-menu-item index="/workers">
          <el-icon><Monitor /></el-icon>
          <span>Worker 监控</span>
        </el-menu-item>
        <el-menu-item index="/mocks">
          <el-icon><Connection /></el-icon>
          <span>Mock 服务</span>
        </el-menu-item>
        <el-menu-item index="/benchmarks">
          <el-icon><TrendCharts /></el-icon>
          <span>性能压测</span>
        </el-menu-item>
        <el-menu-item index="/pipelines">
          <el-icon><SetUp /></el-icon>
          <span>CI/CD</span>
        </el-menu-item>
        <el-menu-item v-if="authStore.isAdmin" index="/users">
          <el-icon><User /></el-icon>
          <span>用户权限</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <span class="header-title">接口自动化测试平台</span>
        <div class="header-user" v-if="authStore.user">
          <el-tag size="small" :type="roleTagType">{{ authStore.user.role }}</el-tag>
          <span class="user-name">{{ authStore.user.display_name || authStore.user.username }}</span>
          <el-button text size="small" @click="authStore.logout()">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()
const activeMenu = computed(() => route.path)
const roleTagType = computed(() => {
  switch (authStore.user?.role) {
    case 'admin': return 'danger'
    case 'manager': return 'warning'
    default: return 'info'
  }
})

onMounted(() => {
  authStore.initFromStorage()
})
</script>

<style>
body {
  margin: 0;
  padding: 0;
}
.app-container {
  height: 100vh;
}
.app-aside {
  background-color: #001529;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo h2 {
  color: #fff;
  margin: 0;
  font-size: 18px;
}
.app-header {
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-title {
  font-size: 16px;
  font-weight: 500;
}
.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-name {
  font-size: 14px;
  color: #606266;
}
</style>
