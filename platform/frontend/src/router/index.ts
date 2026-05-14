import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/cases',
    name: 'Cases',
    component: () => import('../views/Cases.vue'),
  },
  {
    path: '/executions',
    name: 'Executions',
    component: () => import('../views/Executions.vue'),
  },
  {
    path: '/environments',
    name: 'Environments',
    component: () => import('../views/Environments.vue'),
  },
  {
    path: '/workers',
    name: 'Workers',
    component: () => import('../views/Workers.vue'),
  },
  {
    path: '/mocks',
    name: 'Mocks',
    component: () => import('../views/Mocks.vue'),
  },
  {
    path: '/benchmarks',
    name: 'Benchmarks',
    component: () => import('../views/Benchmarks.vue'),
  },
  {
    path: '/pipelines',
    name: 'Pipelines',
    component: () => import('../views/Pipelines.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
