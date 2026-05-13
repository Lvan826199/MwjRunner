<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用例管理</span>
          <el-button type="primary" :icon="Plus">新建用例</el-button>
        </div>
      </template>
      <el-empty description="暂无用例，点击右上角新建" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
