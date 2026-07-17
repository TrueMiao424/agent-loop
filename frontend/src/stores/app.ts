import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configApi, projectApi, sessionApi, taskApi, webhookApi } from '@/api'
import type { AgentSession, Project, Task, WebhookMessage } from '@/types'

export const useAppStore = defineStore('app', () => {
  const projects = ref<Project[]>([])
  const tasks = ref<Task[]>([])
  const webhooks = ref<WebhookMessage[]>([])
  const sessions = ref<AgentSession[]>([])
  const webhookTotal = ref(0)
  const webhookPage = ref(1)
  const webhookPageSize = ref(20)
  const sessionTotal = ref(0)
  const sessionPage = ref(1)
  const sessionPageSize = ref(20)
  const sessionProcessingCount = ref(0)
  const selectedProjectId = ref<number | null>(null)
  const selectedTaskId = ref<number | null>(null)
  const resumableTasks = ref<Task[]>([])
  const polling = ref(true)
  const maxConcurrentSessions = ref(2)
  let refreshing = false

  async function loadPublicConfig() {
    try {
      const cfg = await configApi.get()
      if (cfg?.maxConcurrentSessions) {
        maxConcurrentSessions.value = cfg.maxConcurrentSessions
      }
    } catch {
      /* backend may be starting */
    }
  }

  async function loadProjects() {
    projects.value = await projectApi.list()
    if (!selectedProjectId.value && projects.value.length) {
      selectedProjectId.value = projects.value[0].id
    }
  }

  async function loadTasks() {
    if (!selectedProjectId.value) return
    tasks.value = await taskApi.list(selectedProjectId.value)
    if (selectedTaskId.value && !tasks.value.some((t) => t.id === selectedTaskId.value)) {
      selectedTaskId.value = tasks.value[0]?.id ?? null
    } else if (!selectedTaskId.value && tasks.value.length) {
      selectedTaskId.value = tasks.value[0].id
    }
  }

  function clampPage(page: number, total: number, pageSize: number) {
    const maxPage = Math.max(1, Math.ceil((total || 0) / pageSize) || 1)
    return Math.min(Math.max(1, page), maxPage)
  }

  async function loadWebhooks() {
    const data = await webhookApi.list({
      page: webhookPage.value,
      pageSize: webhookPageSize.value,
    })
    webhooks.value = data.items || []
    webhookTotal.value = data.total || 0
    if (data.pageSize) webhookPageSize.value = data.pageSize
    const nextPage = clampPage(data.page || webhookPage.value, webhookTotal.value, webhookPageSize.value)
    if (nextPage !== webhookPage.value && webhookTotal.value > 0 && !(data.items || []).length) {
      webhookPage.value = nextPage
      return loadWebhooks()
    }
    webhookPage.value = nextPage
  }

  async function loadSessions() {
    const data = await sessionApi.list({
      page: sessionPage.value,
      pageSize: sessionPageSize.value,
    })
    sessions.value = data.items || []
    sessionTotal.value = data.total || 0
    sessionProcessingCount.value = data.processingCount ?? 0
    if (data.pageSize) sessionPageSize.value = data.pageSize
    const nextPage = clampPage(data.page || sessionPage.value, sessionTotal.value, sessionPageSize.value)
    if (nextPage !== sessionPage.value && sessionTotal.value > 0 && !(data.items || []).length) {
      sessionPage.value = nextPage
      return loadSessions()
    }
    sessionPage.value = nextPage
  }

  async function loadResumable() {
    resumableTasks.value = await taskApi.resumable()
  }

  async function refreshAll() {
    if (refreshing) return
    refreshing = true
    try {
      await loadProjects()
      await loadTasks()
      await Promise.all([loadWebhooks(), loadSessions(), loadResumable()])
    } finally {
      refreshing = false
    }
  }

  function selectTask(id: number | null) {
    selectedTaskId.value = id
  }

  async function setWebhookPage(page: number, pageSize?: number) {
    webhookPage.value = page
    if (pageSize) webhookPageSize.value = pageSize
    await loadWebhooks()
  }

  async function setSessionPage(page: number, pageSize?: number) {
    sessionPage.value = page
    if (pageSize) sessionPageSize.value = pageSize
    await loadSessions()
  }

  return {
    projects,
    tasks,
    webhooks,
    sessions,
    webhookTotal,
    webhookPage,
    webhookPageSize,
    sessionTotal,
    sessionPage,
    sessionPageSize,
    sessionProcessingCount,
    resumableTasks,
    polling,
    maxConcurrentSessions,
    selectedProjectId,
    selectedTaskId,
    loadPublicConfig,
    loadProjects,
    loadTasks,
    loadWebhooks,
    loadSessions,
    loadResumable,
    refreshAll,
    selectTask,
    setWebhookPage,
    setSessionPage,
  }
})
