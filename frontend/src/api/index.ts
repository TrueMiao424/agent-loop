import http from './http'
import type { AgentSession, PageResult, Project, Task, WebhookMessage } from '@/types'

export const authApi = {
  login: (username: string, password: string) => http.post('/auth/login/', { username, password }),
  register: (username: string, password: string, displayName?: string) =>
    http.post('/auth/register/', { username, password, display_name: displayName || '' }),
  refresh: (refresh: string) => http.post('/auth/refresh/', { refresh }),
  me: () => http.get('/auth/me/'),
}

export const projectApi = {
  list: () => http.get<Project[]>('/projects/'),
  create: (data: Partial<Project>) => http.post<Project>('/projects/', data),
  update: (id: number, data: Partial<Project>) => http.put<Project>(`/projects/${id}/`, data),
}

export const taskApi = {
  list: (projectId: number) => http.get<Task[]>(`/tasks/?projectId=${projectId}`),
  get: (id: number) => http.get<Task>(`/tasks/${id}/`),
  create: (data: { projectId: number; title: string; acceptanceCriteria: string }, idemKey?: string) =>
    http.post<Task>('/tasks/', data, { headers: idemKey ? { 'X-Idempotency-Key': idemKey } : {} }),
  update: (id: number, data: Partial<Task>) => http.put<Task>(`/tasks/${id}/`, data),
  review1: (id: number, confirmed_files: string[], sub_tasks: Task['subTasks']) =>
    http.post<Task>(`/tasks/${id}/review1/`, { confirmed_files, sub_tasks }),
  review2: (id: number) => http.post<Task>(`/tasks/${id}/review2/`),
  opinion: (id: number, opinion: string, reject = false) =>
    http.post<Task>(`/tasks/${id}/opinion/`, { opinion, reject }),
  interrupt: (id: number) => http.post<Task>(`/tasks/${id}/interrupt/`),
  cancel: (id: number) => http.post<Task>(`/tasks/${id}/cancel/`),
  resume: (id: number) => http.post<Task>(`/tasks/${id}/resume/`),
  resumable: () => http.get<Task[]>('/tasks/resumable/'),
}

export const sessionApi = {
  list: (params?: { page?: number; pageSize?: number }) =>
    http.get<PageResult<AgentSession>>('/sessions/', { params }),
  reset: () => http.post('/sessions/reset/'),
}

export const webhookApi = {
  list: (params?: { page?: number; pageSize?: number }) =>
    http.get<PageResult<WebhookMessage>>('/webhooks/', { params }),
}

export const configApi = {
  get: () =>
    http.get<{ maxConcurrentSessions: number; agentPreferAnthropicApi: boolean }>('/config/'),
}

export const settingsApi = {
  get: () => http.get('/settings/'),
  save: (data: unknown) => http.post('/settings/', data),
  test: () =>
    http.post<{ ok: boolean; model: string; baseUrl: string; reply: string }>(
      '/settings/test/',
      {},
      { timeout: 120000 },
    ),
}

export const feishuApi = {
  status: () =>
    http.get<{
      enabled: boolean
      status: string
      error?: string
      endpoint: string
      heartbeat: string
      using: string
    }>('/feishu/long-connection/status/'),
  logs: () => http.get<string[]>('/feishu/long-connection/logs/'),
  restart: () => http.post('/feishu/long-connection/restart/'),
  chats: () => http.get<Array<{ chatId: string; name: string; description?: string }>>('/feishu/chats/'),
}
