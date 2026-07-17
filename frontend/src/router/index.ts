import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue') },
    { path: '/register', component: () => import('@/views/RegisterView.vue') },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { auth: true },
      children: [
        { path: '', redirect: '/kanban' },
        { path: 'kanban', component: () => import('@/views/KanbanView.vue') },
        { path: 'tasks', component: () => import('@/views/TaskWorkplaceView.vue') },
        { path: 'messages', component: () => import('@/views/MessagesView.vue') },
        { path: 'logs', component: () => import('@/views/LogsView.vue') },
        { path: 'sessions', component: () => import('@/views/SessionsView.vue') },
        { path: 'settings', component: () => import('@/views/SettingsView.vue') },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.auth && !auth.token) return '/login'
  if ((to.path === '/login' || to.path === '/register') && auth.token) return '/kanban'
})

export default router
