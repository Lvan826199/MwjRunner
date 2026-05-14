import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, setTokens, clearTokens, getAccessToken, getRefreshToken, type UserInfo } from '@/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const isAuthenticated = computed(() => !!getAccessToken())
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isManager = computed(() => user.value?.role === 'admin' || user.value?.role === 'manager')

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password })
    const { access_token, refresh_token, user: userInfo } = res.data
    setTokens(access_token, refresh_token)
    user.value = userInfo
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch { /* ignore */ }
    clearTokens()
    user.value = null
    router.push('/login')
  }

  async function fetchUser() {
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      clearTokens()
      user.value = null
    }
  }

  function initFromStorage() {
    const token = getAccessToken()
    if (token) {
      fetchUser()
    }
  }

  return { user, isAuthenticated, isAdmin, isManager, login, logout, fetchUser, initFromStorage }
})
