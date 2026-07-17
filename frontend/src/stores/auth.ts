import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const username = ref(localStorage.getItem('username') || '')

  function persistSession(data: { access: string; refresh: string; user: { username: string } }) {
    token.value = data.access
    username.value = data.user.username
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    localStorage.setItem('username', data.user.username)
  }

  async function login(user: string, pass: string) {
    persistSession((await authApi.login(user, pass)) as any)
  }

  async function register(user: string, pass: string, displayName?: string) {
    persistSession((await authApi.register(user, pass, displayName)) as any)
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('username')
  }

  return { token, username, login, register, logout }
})
