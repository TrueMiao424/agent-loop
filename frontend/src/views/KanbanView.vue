<template>
  <div class="kanban page-card">
    <div class="page-header">
      <div>
        <h2>需求看板</h2>
        <p>跟踪每个需求在 Agent 工作流中的当前阶段</p>
      </div>
      <div class="page-header-actions">
        <el-button type="primary" :icon="Plus" round @click="showCreate = true">新建需求</el-button>
      </div>
    </div>

    <div class="columns">
      <div v-for="(step, idx) in steps" :key="step" class="column">
        <div class="column-head" :style="{ '--step-color': STEP_COLORS[step] }">
          <span class="step-num">{{ idx + 1 }}</span>
          <div>
            <h3>{{ STEP_LABELS[step] }}</h3>
            <span class="count">{{ tasksByStep(step).length }} 个任务</span>
          </div>
        </div>
        <div class="column-body">
          <div
            v-for="task in tasksByStep(step)"
            :key="task.id"
            class="task-card"
            @click="openTask(task.id)"
          >
            <div class="task-card-top">
              <span class="task-id">#{{ task.id }}</span>
              <span :class="['status-badge', statusClass(task.currentStatus)]">
                {{ STATUS_LABELS[task.currentStatus] || task.currentStatus }}
              </span>
            </div>
            <strong class="task-title">{{ task.title }}</strong>
            <p class="task-time">{{ formatTime(task.updatedAt) }}</p>
            <el-tag v-if="task.currentStatus === 'Interrupted'" type="warning" size="small" round>
              可续做
            </el-tag>
          </div>
          <div v-if="!tasksByStep(step).length" class="column-empty">暂无任务</div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreate" title="新建需求" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="简要描述需求" />
        </el-form-item>
        <el-form-item label="验收标准 (PRD)">
          <el-input
            v-model="form.acceptanceCriteria"
            type="textarea"
            :rows="6"
            placeholder="详细描述功能要求、验收条件..."
          />
        </el-form-item>
        <p class="create-hint">提交前请先在「配置管理」保存您自己的 Anthropic API Key</p>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createTask">提交需求</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { taskApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { STEP_COLORS, STEP_LABELS, STATUS_LABELS, TaskStep } from '@/types'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const router = useRouter()
const showCreate = ref(false)
const form = reactive({ title: '', acceptanceCriteria: '' })

const steps = Object.values(TaskStep)

function tasksByStep(step: string) {
  return store.tasks.filter((t) => t.currentStep === step)
}

function statusClass(status: string) {
  const map: Record<string, string> = {
    Init: 'status-init',
    Processing: 'status-processing',
    Finished: 'status-finished',
    Failed: 'status-failed',
    Interrupted: 'status-interrupted',
    Cancelled: 'status-cancelled',
  }
  return map[status] || 'status-init'
}

function formatTime(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function openTask(id: number) {
  store.selectTask(id)
  router.push({ path: '/tasks', query: { taskId: String(id) } })
}

async function createTask() {
  if (!store.selectedProjectId) return ElMessage.warning('请先选择项目')
  if (!form.title.trim()) return ElMessage.warning('请填写标题')
  try {
    await taskApi.create({
      projectId: store.selectedProjectId,
      title: form.title,
      acceptanceCriteria: form.acceptanceCriteria,
    })
    showCreate.value = false
    form.title = ''
    form.acceptanceCriteria = ''
    ElMessage.success('需求已提交，Agent 将自动编排')
    await store.refreshAll()
  } catch (e: any) {
    const msg = e?.response?.data?.msg || e?.message || '创建失败'
    ElMessage.error(msg)
  }
}
</script>

<style scoped>
.columns {
  display: grid;
  grid-template-columns: repeat(5, minmax(200px, 1fr));
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.column {
  background: var(--bg-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  min-height: 420px;
  display: flex;
  flex-direction: column;
}

.column-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
  border-top: 3px solid var(--step-color);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.step-num {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--step-color);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 700;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.column-head h3 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
}

.count {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.column-body {
  flex: 1;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.task-card:hover {
  border-color: var(--accent);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.task-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-id {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--accent);
}

.task-title {
  display: block;
  font-size: 0.875rem;
  line-height: 1.4;
  margin-bottom: 6px;
}

.task-time {
  margin: 0 0 8px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.column-empty {
  flex: 1;
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-size: 0.8125rem;
  border: 2px dashed var(--border);
  border-radius: var(--radius-sm);
  min-height: 80px;
}

.create-hint {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
</style>
