import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const http = axios.create({ baseURL: '/api', timeout: 30000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  config.headers['X-Trace-Id'] = crypto.randomUUID()
  return config
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body.success === 'boolean') {
      if (!body.success) {
        ElMessage.error(body.msg || '请求失败')
        return Promise.reject(body)
      }
      return body.data
    }
    return resp.data
  },
  async (err) => {
    const status = err.response?.status
    if (status === 401) {
      const auth = useAuthStore()
      const refresh = localStorage.getItem('refresh_token')
      const isRefreshCall = err.config?.url?.includes('/auth/refresh/')
      if (refresh && !isRefreshCall && !err.config._retried) {
        try {
          err.config._retried = true
          const resp = await axios.post(
            '/api/auth/refresh/',
            { refresh },
            { headers: { 'Content-Type': 'application/json' } },
          )
          const access = resp.data?.access
          if (access) {
            auth.token = access
            localStorage.setItem('access_token', access)
            err.config.headers.Authorization = `Bearer ${access}`
            return http.request(err.config)
          }
        } catch {
          /* fall through to logout */
        }
      }
      auth.logout()
      if (router.currentRoute.value.path !== '/login') {
        ElMessage.warning('登录已过期，请重新登录')
        router.push('/login')
      }
      return Promise.reject(err)
    }
    ElMessage.error(err.response?.data?.msg || err.message || '网络错误')
    return Promise.reject(err)
  },
)

export default http
