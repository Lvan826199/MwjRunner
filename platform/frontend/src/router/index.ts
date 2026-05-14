import { createRouter, createWebHistory } from 'vue-router'
import { getAccessToken } from '@/api'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
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
    path: '/executions/:id',
    name: 'ExecutionDetail',
    component: () => import('../views/ExecutionDetail.vue'),
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
  {
    path: '/users',
    name: 'Users',
    component: () => import('../views/Users.vue'),
    meta: { roles: ['admin'] },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const token = getAccessToken()

  if (to.meta.public) {
    // 已登录访问登录页，跳转首页
    if (token && to.path === '/login') {
      next('/')
    } else {
      next()
    }
    return
  }

  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  next()
})

export default router
