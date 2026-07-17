<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon">
          <el-icon :size="20"><Cpu /></el-icon>
        </div>
        <div>
          <strong>Agent Loop</strong>
          <span>需求编排平台</span>
        </div>
      </div>

      <nav class="nav">
        <router-link v-for="tab in tabs" :key="tab.path" :to="tab.path" class="nav-item">
          <el-icon :size="18"><component :is="tab.icon" /></el-icon>
          <span>{{ tab.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-chip">
          <el-icon :size="16"><User /></el-icon>
          <span>{{ auth.username || 'admin' }}</span>
        </div>
        <el-button link class="logout-btn" @click="logout">
          <el-icon><SwitchButton /></el-icon>
          退出
        </el-button>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="topbar-left">
          <el-select
            v-model="store.selectedProjectId"
            placeholder="选择项目"
            class="project-select"
          >
            <el-option v-for="p in store.projects" :key="p.id" :label="p.projectName" :value="p.id" />
          </el-select>
          <el-button :icon="Plus" round @click="openCreateProject">新建项目</el-button>
          <el-button :disabled="!store.selectedProjectId" round @click="openEditProject">编辑项目</el-button>
        </div>
        <div class="topbar-right">
          <div class="stat-pill">
            <span class="stat-label">任务</span>
            <span class="stat-value">{{ store.tasks.length }}</span>
          </div>
          <div class="stat-pill">
            <span class="stat-label">Session</span>
            <span class="stat-value">{{ store.sessionProcessingCount }}/{{ store.maxConcurrentSessions }}</span>
          </div>
          <el-switch v-model="store.polling" active-text="自动刷新" />
        </div>
      </header>

      <el-alert
        v-if="store.resumableTasks.length"
        type="warning"
        show-icon
        :closable="false"
        class="resume-banner"
        title="检测到中断/失败任务，可一键续做"
      >
        <template #default>
          <div v-for="t in store.resumableTasks" :key="t.id" class="resume-row">
            <span>#{{ t.id }} {{ t.title }} · {{ STEP_LABELS[t.currentStep] }}</span>
            <el-button size="small" type="primary" round @click="resumeTask(t.id)">续做</el-button>
          </div>
        </template>
      </el-alert>

      <main class="content">
        <router-view />
      </main>
    </div>

    <el-dialog v-model="showProject" :title="projectDialogTitle" width="520px" destroy-on-close>
      <el-form label-width="120px" label-position="top">
        <el-form-item label="项目名称">
          <el-input v-model="projectForm.projectName" placeholder="例如：订单服务" />
        </el-form-item>
        <el-form-item label="代码路径">
          <el-input v-model="projectForm.projectPath" placeholder="沙箱中仓库绝对路径" />
        </el-form-item>
        <el-form-item label="Git 远程仓库">
          <el-input v-model="projectForm.gitRemoteUrl" placeholder="https://github.com/org/repo.git" />
        </el-form-item>
        <el-form-item label="Git 分支">
          <el-input v-model="projectForm.gitBranch" placeholder="main" />
        </el-form-item>
        <el-form-item label="发布时 Git Push">
          <el-switch v-model="projectForm.gitPushEnabled" active-text="开启" inactive-text="仅 commit" />
        </el-form-item>
        <el-form-item label="编码规范路径">
          <el-input v-model="projectForm.conventionPath" placeholder=".github/coding_style.md" />
        </el-form-item>
        <el-form-item label="飞书群 chat_id">
          <el-input v-model="projectForm.chatGroupId" placeholder="oc_xxx" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProject = false">取消</el-button>
        <el-button type="primary" @click="saveProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChatDotRound,
  Cpu,
  Document,
  Grid,
  Monitor,
  Plus,
  Setting,
  SwitchButton,
  User,
  VideoPlay,
} from '@element-plus/icons-vue'
import { projectApi, taskApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { STEP_LABELS } from '@/types'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const auth = useAuthStore()
const router = useRouter()
const showProject = ref(false)
const projectMode = ref<'create' | 'edit'>('create')
const projectForm = reactive({
  projectName: '',
  projectPath: '',
  chatGroupId: '',
  conventionPath: '.github/coding_style.md',
  gitRemoteUrl: '',
  gitBranch: 'main',
  gitPushEnabled: false,
})
const projectDialogTitle = computed(() => (projectMode.value === 'create' ? '新建项目' : '编辑项目'))
let timer: number | undefined

const tabs = [
  { path: '/kanban', label: '需求看板', icon: Grid },
  { path: '/tasks', label: '需求工作台', icon: Document },
  { path: '/messages', label: '协作消息', icon: ChatDotRound },
  { path: '/logs', label: '执行终端', icon: VideoPlay },
  { path: '/sessions', label: '控制台', icon: Monitor },
  { path: '/settings', label: '配置管理', icon: Setting },
]

async function bootstrap() {
  await store.loadPublicConfig()
  await store.loadProjects()
  if (store.selectedProjectId) {
    await store.loadTasks()
  }
  await Promise.all([store.loadWebhooks(), store.loadSessions(), store.loadResumable()])
}

function openCreateProject() {
  projectMode.value = 'create'
  projectForm.projectName = ''
  projectForm.projectPath = ''
  projectForm.chatGroupId = ''
  projectForm.conventionPath = '.github/coding_style.md'
  projectForm.gitRemoteUrl = ''
  projectForm.gitBranch = 'main'
  projectForm.gitPushEnabled = false
  showProject.value = true
}

function openEditProject() {
  const p = store.projects.find((x) => x.id === store.selectedProjectId)
  if (!p) return
  projectMode.value = 'edit'
  projectForm.projectName = p.projectName
  projectForm.projectPath = p.projectPath
  projectForm.chatGroupId = p.chatGroupId
  projectForm.conventionPath = p.conventionPath || '.github/coding_style.md'
  projectForm.gitRemoteUrl = p.gitRemoteUrl || ''
  projectForm.gitBranch = p.gitBranch || 'main'
  projectForm.gitPushEnabled = !!p.gitPushEnabled
  showProject.value = true
}

function startPolling() {
  stopPolling()
  timer = window.setInterval(() => {
    if (store.polling) store.refreshAll()
  }, 5000)
}

function stopPolling() {
  if (timer) window.clearInterval(timer)
}

async function onProjectChange() {
  store.selectedTaskId = null
  await store.loadTasks()
}

async function saveProject() {
  if (projectMode.value === 'create') {
    await projectApi.create(projectForm)
    ElMessage.success('项目已创建')
  } else if (store.selectedProjectId) {
    await projectApi.update(store.selectedProjectId, projectForm)
    ElMessage.success('项目已更新')
  }
  showProject.value = false
  await bootstrap()
}

async function resumeTask(id: number) {
  await taskApi.resume(id)
  ElMessage.success('任务已续做，正在重新调度')
  store.selectTask(id)
  await store.refreshAll()
  router.push({ path: '/tasks', query: { taskId: String(id) } })
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  await bootstrap()
  startPolling()
})

onUnmounted(stopPolling)

watch(() => store.selectedProjectId, onProjectChange)
</script>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-sidebar);
  color: var(--text-inverse);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: grid;
  place-items: center;
  color: #fff;
}

.brand strong {
  display: block;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand span {
  font-size: 0.75rem;
  color: #94a3b8;
}

.nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  text-decoration: none;
  color: #94a3b8;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: var(--bg-sidebar-hover);
  color: #e2e8f0;
}

.nav-item.router-link-active {
  background: var(--bg-sidebar-active);
  color: #fff;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8125rem;
  color: #94a3b8;
}

.logout-btn {
  color: #94a3b8 !important;
  font-size: 0.8125rem;
}

.logout-btn:hover {
  color: #f87171 !important;
}

.main {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  height: var(--header-height);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 50;
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-select {
  width: 220px;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: var(--bg-muted);
  border-radius: 999px;
  font-size: 0.8125rem;
}

.stat-label {
  color: var(--text-muted);
}

.stat-value {
  font-weight: 700;
  color: var(--accent);
}

.resume-banner {
  margin: 16px 28px 0;
  border-radius: var(--radius-md);
}

.resume-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 6px;
}

.content {
  flex: 1;
  padding: 24px 28px 32px;
}
</style>
