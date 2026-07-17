<template>
  <div class="workplace">
    <aside class="task-sidebar page-card">
      <div class="sidebar-head">
        <h3>任务列表</h3>
        <el-tag size="small" round>{{ store.tasks.length }}</el-tag>
      </div>
      <div class="task-list">
        <div
          v-for="t in store.tasks"
          :key="t.id"
          class="task-item"
          :class="{ active: t.id === store.selectedTaskId }"
          @click="store.selectedTaskId = t.id"
        >
          <div class="task-item-top">
            <span class="task-item-id">#{{ t.id }}</span>
            <span :class="['status-badge', statusClass(t.currentStatus)]">
              {{ STATUS_LABELS[t.currentStatus] || t.currentStatus }}
            </span>
          </div>
          <span class="task-item-title">{{ t.title }}</span>
          <span class="task-item-step">{{ STEP_LABELS[t.currentStep] }}</span>
        </div>
        <div v-if="!store.tasks.length" class="empty-hint">暂无任务</div>
      </div>
    </aside>

    <section v-if="task" class="task-detail page-card">
      <div class="detail-header">
        <div>
          <div class="detail-breadcrumb">
            <span :class="['status-badge', statusClass(task.currentStatus)]">
              {{ STATUS_LABELS[task.currentStatus] }}
            </span>
            <span class="step-label">{{ STEP_LABELS[task.currentStep] }}</span>
          </div>
          <h2>#{{ task.id }} {{ task.title }}</h2>
        </div>
        <div class="detail-actions">
          <el-button
            v-if="canInterrupt"
            type="warning"
            round
            :icon="VideoPause"
            :loading="interrupting"
            @click="interrupt"
          >
            中断
          </el-button>
          <el-button
            v-if="canResume"
            type="primary"
            round
            :icon="VideoPlay"
            :loading="resuming"
            @click="resume"
          >
            续做
          </el-button>
          <el-button
            v-if="canCancel"
            type="danger"
            plain
            round
            :loading="cancelling"
            @click="cancelTask"
          >
            取消任务
          </el-button>
        </div>
      </div>

      <div class="stepper">
        <div
          v-for="(step, idx) in stepOrder"
          :key="step"
          class="stepper-item clickable"
          :class="{
            active: selectedStep === step,
            done: stepIndex(task.currentStep) > idx || task.currentStatus === 'Finished',
          }"
          @click="selectStep(step)"
        >
          <div class="stepper-dot" :style="{ '--c': STEP_COLORS[step] }">{{ idx + 1 }}</div>
          <span class="stepper-label">{{ STEP_LABELS[step] }}</span>
          <span v-if="stepRunCount(step)" class="stepper-runs">×{{ stepRunCount(step) }}</span>
        </div>
      </div>

      <el-alert
        v-if="task.autoReview && !task.autoReview.skipped && isOnReviewStep"
        :type="task.autoReview.passed ? 'success' : 'warning'"
        show-icon
        :closable="false"
        :title="task.autoReview.passed ? '自动 Review 通过' : '自动 Review 发现问题'"
        class="alert-block"
      >
        <template #default>
          <p>{{ task.autoReview.summary }}</p>
          <ul v-if="(task.autoReview.issues || []).length" class="auto-review-issues">
            <li v-for="(issue, i) in task.autoReview.issues" :key="i">{{ issue }}</li>
          </ul>
        </template>
      </el-alert>

      <el-alert
        v-if="task.currentStatus === 'Interrupted'"
        type="warning"
        show-icon
        :closable="false"
        title="任务已中断"
        description="点击「续做」将从 checkpoint 恢复并立即重新调度；或点「取消任务」永久结束"
        class="alert-block"
      />

      <el-alert
        v-if="task.currentStatus === 'Failed' && task.failReason"
        type="error"
        show-icon
        :closable="false"
        title="任务失败"
        :description="task.failReason"
        class="alert-block"
      />

      <el-alert
        v-if="task.currentStatus === 'Cancelled'"
        type="info"
        show-icon
        :closable="false"
        title="任务已取消"
        description="流程已结束，不可续做。如需继续，请新建任务。"
        class="alert-block"
      />

      <el-alert
        v-if="agentSourceLabel"
        :type="agentSourceType"
        show-icon
        :closable="false"
        :title="`Agent 来源: ${agentSourceLabel}`"
        :description="agentSourceHint"
        class="alert-block"
      />

      <div v-if="(task.reviewAudit || []).length" class="section-block audit-block">
        <h4 class="section-title">Review 审计</h4>
        <ul class="audit-list">
          <li v-for="(a, idx) in task.reviewAudit" :key="idx">
            <span class="audit-action">{{ auditActionLabel(a.action) }}</span>
            <span class="audit-user">{{ a.username }}</span>
            <span class="audit-time">{{ formatAuditTime(a.at) }}</span>
          </li>
        </ul>
      </div>

      <div class="section-block" style="margin-top: 0; padding-top: 0; border-top: none">
        <h4 class="section-title">验收标准</h4>
        <el-input v-model="criteria" type="textarea" :rows="4" placeholder="PRD / 验收标准" />
        <el-button size="small" style="margin-top: 10px" round :loading="savingCriteria" @click="saveCriteria">保存验收标准</el-button>
      </div>

      <div class="section-block">
        <h4 class="section-title">Review 意见</h4>
        <el-input v-model="opinion" type="textarea" :rows="2" placeholder="填写审查意见，驳回后将按阶段重新执行..." />
        <div class="opinion-actions">
          <el-button
            v-if="canRejectReview"
            size="small"
            type="warning"
            round
            :loading="rejecting"
            @click="submitOpinionReject"
          >
            提交意见并重新执行
          </el-button>
          <el-button size="small" round :loading="savingOpinion" @click="saveOpinionDraft">仅保存意见</el-button>
        </div>
        <p v-if="canRejectReview" class="review-hint">
          Review 1 驳回将重新拆解需求；Review 2 驳回将重新生成代码
        </p>
      </div>

      <div v-if="selectedStepDetail" class="section-block history-block">
        <div class="history-head">
          <h4 class="section-title">
            {{ STEP_LABELS[selectedStep] }} · 执行历史
            <el-tag v-if="selectedRun" size="small" round>第 {{ selectedRun.run }} 轮</el-tag>
          </h4>
          <div v-if="selectedStepRuns.length > 1" class="run-tabs">
            <el-button
              v-for="run in selectedStepRuns"
              :key="`${run.step}-${run.run}`"
              size="small"
              :type="selectedRun?.run === run.run ? 'primary' : 'default'"
              round
              @click="selectedRun = run"
            >
              第{{ run.run }}轮
            </el-button>
          </div>
        </div>

        <template v-if="displayRun">
          <div v-if="displayRun.acceptanceCriteria && selectedStep === 'Requirement_Refinement'" class="history-section">
            <h5>需求描述</h5>
            <pre class="history-pre">{{ displayRun.acceptanceCriteria }}</pre>
          </div>

          <div
            v-if="(displayRun.subTasks || []).length && ['Requirement_Refinement', 'Human_Review_1'].includes(selectedStep)"
            class="history-section"
          >
            <h5>子任务清单</h5>
            <ul class="history-subtasks">
              <li v-for="st in displayRun.subTasks" :key="st.id">
                <el-tag size="small" :type="st.completed ? 'success' : 'info'" round>
                  {{ st.completed ? '完成' : '待办' }}
                </el-tag>
                {{ st.title }}
              </li>
            </ul>
          </div>

          <div
            v-if="displayRun.affectedFiles && ['Requirement_Refinement', 'Human_Review_1'].includes(selectedStep)"
            class="history-section"
          >
            <h5>影响文件</h5>
            <div class="tag-group">
              <el-tag
                v-for="f in [
                  ...(displayRun.affectedFiles.predicted_by_agent || []),
                  ...(displayRun.affectedFiles.confirmed_by_human || []),
                ]"
                :key="f"
                round
                effect="plain"
              >
                {{ f }}
              </el-tag>
            </div>
          </div>

          <div v-if="(displayRun.codeDiffs || []).length && ['Auto_Development', 'Human_Review_2'].includes(selectedStep)" class="history-section">
            <h5>代码变更</h5>
            <div v-for="d in displayRun.codeDiffs" :key="d.filePath" class="diff-block">
              <div class="diff-file">{{ d.filePath }}</div>
              <pre v-if="d.modified" class="terminal mono diff-code">{{ d.modified }}</pre>
              <pre v-else class="terminal mono">{{ d.diffText }}</pre>
            </div>
          </div>

          <div v-if="displayRun.reviewOpinion" class="history-section">
            <h5>Review 意见</h5>
            <pre class="history-pre">{{ displayRun.reviewOpinion }}</pre>
          </div>

          <div class="history-section">
            <h5>执行日志</h5>
            <div class="terminal-wrap">
              <pre class="terminal mono">{{ displayRun.executionLogs || '该轮次暂无日志' }}</pre>
            </div>
          </div>
        </template>

        <el-empty v-else description="请从上方步骤条选择要查看的阶段" />
      </div>

      <div v-if="task.currentStep === 'Human_Review_1'" class="section-block review-block">
        <h4 class="section-title">Review 1 · 确认文件与子任务</h4>
        <div class="tag-group">
          <el-tag
            v-for="f in confirmedFiles"
            :key="f"
            closable
            round
            effect="plain"
            @close="removeFile(f)"
          >
            {{ f }}
          </el-tag>
        </div>
        <div class="inline-form">
          <el-input v-model="newFile" placeholder="添加文件路径" style="flex: 1" />
          <el-button @click="addFile">添加</el-button>
        </div>
        <div v-if="editableSubTasks.length" class="subtask-list">
          <div v-for="st in editableSubTasks" :key="st.id" class="subtask-row">
            <el-checkbox v-model="st.completed" />
            <el-input v-model="st.title" size="small" />
          </div>
        </div>
        <el-button type="success" round style="margin-top: 12px" :loading="reviewing1" @click="approveReview1">
          同意动工
        </el-button>
      </div>

      <div v-if="task.currentStep === 'Human_Review_2'" class="section-block review-block">
        <h4 class="section-title">Review 2 · 代码变更</h4>
        <div v-for="d in task.codeDiffs || []" :key="d.filePath" class="diff-block">
          <div class="diff-file">{{ d.filePath }}</div>
          <pre v-if="d.modified" class="terminal mono diff-code">{{ d.modified }}</pre>
          <pre v-else class="terminal mono">{{ d.diffText }}</pre>
        </div>
        <el-empty v-if="!(task.codeDiffs || []).length" description="暂无代码 diff" />
        <el-button type="success" round style="margin-top: 12px" :loading="reviewing2" @click="approveReview2">
          合并发布
        </el-button>
        <p class="review-hint">通过后将在项目目录应用 diff、运行自测并 git commit</p>
      </div>

      <div class="section-block">
        <h4 class="section-title">执行日志</h4>
        <div class="terminal-wrap">
          <div class="terminal-header">
            <span class="terminal-dot red" />
            <span class="terminal-dot yellow" />
            <span class="terminal-dot green" />
            <span class="terminal-title">agent-session.log</span>
          </div>
          <pre class="terminal mono">{{ task.executionLogs || '暂无日志，等待 Agent 执行...' }}</pre>
        </div>
      </div>
    </section>

    <div v-else class="empty-panel page-card">
      <el-empty description="从左侧选择一个任务，或前往看板新建需求" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { taskApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { STEP_COLORS, STEP_LABELS, STATUS_LABELS, TaskStatus, TaskStep } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useAppStore()
const route = useRoute()
const criteria = ref('')
const opinion = ref('')
const newFile = ref('')
const confirmedFiles = ref<string[]>([])
const editableSubTasks = ref<{ id: string; title: string; completed: boolean }[]>([])
const interrupting = ref(false)
const cancelling = ref(false)
const resuming = ref(false)
const reviewing1 = ref(false)
const reviewing2 = ref(false)
const savingCriteria = ref(false)
const savingOpinion = ref(false)
const rejecting = ref(false)
const selectedStep = ref<TaskStep | ''>('')
const selectedRun = ref<TaskStepHistory | null>(null)

const stepOrder = Object.values(TaskStep)

const task = computed(() => store.tasks.find((t) => t.id === store.selectedTaskId))

const isOnReviewStep = computed(
  () => task.value?.currentStep === TaskStep.HumanReview1 || task.value?.currentStep === TaskStep.HumanReview2,
)
const canRejectReview = computed(
  () =>
    isOnReviewStep.value &&
    task.value?.currentStatus === TaskStatus.Init,
)

const selectedStepRuns = computed(() => {
  if (!task.value || !selectedStep.value) return []
  return (task.value.executionHistory || [])
    .filter((h) => h.step === selectedStep.value)
    .sort((a, b) => (b.run || 0) - (a.run || 0))
})

const selectedStepDetail = computed(() => !!selectedStep.value)

const liveStepSnapshot = computed((): TaskStepHistory | null => {
  const t = task.value
  if (!t || !selectedStep.value) return null
  return {
    step: selectedStep.value,
    run: stepRunCount(selectedStep.value) + 1,
    acceptanceCriteria: t.acceptanceCriteria,
    subTasks: t.subTasks,
    affectedFiles: t.affectedFiles,
    codeDiffs: t.codeDiffs,
    executionLogs: t.executionLogs,
    reviewOpinion: t.reviewOpinion,
  }
})

const displayRun = computed(() => selectedRun.value || liveStepSnapshot.value)

const agentMeta = computed(() => task.value?.agentMeta?.auto_development || task.value?.agentMeta?.requirement_refinement)
const agentSourceLabel = computed(() => {
  const m = agentMeta.value
  if (!m) return ''
  if (m.fallback) return '本地模拟 (fallback)'
  if (m.source === 'claude_cli') return 'Claude Code CLI'
  if (m.source === 'anthropic_api') return `Anthropic API${m.model ? ` · ${m.model}` : ''}`
  if (m.source === 'gemini') return 'Gemini API'
  return m.source || ''
})
const agentSourceType = computed(() => (agentMeta.value?.fallback ? 'warning' : 'success'))
const agentSourceHint = computed(() =>
  agentMeta.value?.fallback
    ? '当前结果为演示 mock，请在配置管理填写 API Key 以启用真实 Agent'
    : '代码由真实 Agent 生成，Review 2 展示的是完整 modified 源码',
)

function auditActionLabel(action: string) {
  const map: Record<string, string> = {
    review1_approved: 'Review 1 通过',
    review2_approved: 'Review 2 通过',
    review1_rejected: 'Review 1 驳回重拆',
    review2_rejected: 'Review 2 驳回重写',
  }
  return map[action] || action
}

function formatAuditTime(at: string) {
  if (!at) return ''
  return at.replace('T', ' ').slice(0, 19)
}
const canInterrupt = computed(() => task.value?.currentStatus === TaskStatus.Processing)
const canResume = computed(() =>
  [TaskStatus.Interrupted, TaskStatus.Failed].includes(task.value?.currentStatus as TaskStatus),
)
const canCancel = computed(() =>
  ![TaskStatus.Finished, TaskStatus.Cancelled].includes(task.value?.currentStatus as TaskStatus),
)

function stepIndex(step: string) {
  return stepOrder.indexOf(step as TaskStep)
}

function hasStepHistory(step: string) {
  return (task.value?.executionHistory || []).some((h) => h.step === step)
}

function stepRunCount(step: string) {
  const runs = new Set((task.value?.executionHistory || []).filter((h) => h.step === step).map((h) => h.run))
  return runs.size || 0
}

function selectStep(step: TaskStep) {
  selectedStep.value = step
  const runs = (task.value?.executionHistory || []).filter((h) => h.step === step)
  selectedRun.value = runs.length ? runs[runs.length - 1] : null
}

function syncSelectedStep(t: typeof task.value) {
  if (!t) return
  if (!selectedStep.value) {
    selectedStep.value = t.currentStep
  }
  const runs = (t.executionHistory || []).filter((h) => h.step === selectedStep.value)
  if (runs.length) {
    const current = selectedRun.value
    selectedRun.value = runs.find((r) => r.run === current?.run && r.finishedAt === current?.finishedAt) || runs[runs.length - 1]
  } else {
    selectedRun.value = null
  }
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

watch(
  () => route.query.taskId,
  (id) => {
    const n = Number(id)
    if (id && !Number.isNaN(n)) store.selectTask(n)
  },
  { immediate: true },
)

watch(
  task,
  (t) => {
    if (!t) return
    criteria.value = t.acceptanceCriteria
    opinion.value = t.reviewOpinion || ''
    confirmedFiles.value = [
      ...(t.affectedFiles?.predicted_by_agent || []),
      ...(t.affectedFiles?.confirmed_by_human || []),
    ]
    editableSubTasks.value = (t.subTasks || []).map((st) => ({ ...st }))
    syncSelectedStep(t)
  },
  { immediate: true },
)

function addFile() {
  const v = newFile.value.trim()
  if (v) confirmedFiles.value.push(v)
  newFile.value = ''
}
function removeFile(f: string) {
  confirmedFiles.value = confirmedFiles.value.filter((x) => x !== f)
}

async function saveCriteria() {
  if (!task.value) return
  savingCriteria.value = true
  try {
    await taskApi.update(task.value.id, { acceptanceCriteria: criteria.value })
    ElMessage.success('验收标准已保存')
    await store.refreshAll()
  } finally {
    savingCriteria.value = false
  }
}

async function approveReview1() {
  if (!task.value) return
  reviewing1.value = true
  try {
    await taskApi.review1(task.value.id, confirmedFiles.value, editableSubTasks.value)
    ElMessage.success('Review 1 已通过')
    await store.refreshAll()
  } finally {
    reviewing1.value = false
  }
}

async function approveReview2() {
  if (!task.value) return
  reviewing2.value = true
  try {
    await taskApi.review2(task.value.id)
    ElMessage.success('Review 2 已通过，进入发布')
    await store.refreshAll()
  } finally {
    reviewing2.value = false
  }
}

async function saveOpinionDraft() {
  if (!task.value || !opinion.value.trim()) {
    ElMessage.warning('请填写 Review 意见')
    return
  }
  savingOpinion.value = true
  try {
    await taskApi.opinion(task.value.id, opinion.value, false)
    ElMessage.success('意见已保存')
    await store.refreshAll()
  } finally {
    savingOpinion.value = false
  }
}

async function submitOpinionReject() {
  if (!task.value || !opinion.value.trim()) {
    ElMessage.warning('请填写 Review 意见')
    return
  }
  const stepLabel = task.value.currentStep === TaskStep.HumanReview1 ? '重新拆解需求' : '重新生成代码'
  await ElMessageBox.confirm(`确认提交意见并${stepLabel}？`, '驳回确认', { type: 'warning' })
  rejecting.value = true
  try {
    await taskApi.opinion(task.value.id, opinion.value, true)
    ElMessage.success(`意见已提交，正在${stepLabel}`)
    await store.refreshAll()
  } finally {
    rejecting.value = false
  }
}

async function interrupt() {
  if (!task.value) return
  await ElMessageBox.confirm(
    '确认中断当前 Agent 执行？系统将发送取消信号，稍后可从 checkpoint 续做。',
    '中断确认',
    { type: 'warning' },
  )
  interrupting.value = true
  try {
    await taskApi.interrupt(task.value.id)
    ElMessage.warning('任务已中断，可在顶部或此处续做')
    await store.refreshAll()
  } finally {
    interrupting.value = false
  }
}

async function cancelTask() {
  if (!task.value) return
  await ElMessageBox.confirm(
    '确认永久取消该任务？取消后不可续做，如需继续请新建任务。',
    '取消任务',
    { type: 'warning', confirmButtonText: '确认取消', cancelButtonText: '再想想' },
  )
  cancelling.value = true
  try {
    await taskApi.cancel(task.value.id)
    ElMessage.success('任务已取消')
    await store.refreshAll()
  } finally {
    cancelling.value = false
  }
}

async function resume() {
  if (!task.value) return
  resuming.value = true
  try {
    await taskApi.resume(task.value.id)
    ElMessage.success('任务已续做，正在重新调度 Agent')
    await store.refreshAll()
  } finally {
    resuming.value = false
  }
}
</script>

<style scoped>
.workplace {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
}

.task-sidebar {
  padding: 0;
  overflow: hidden;
  position: sticky;
  top: calc(var(--header-height) + 24px);
}

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-light);
}

.sidebar-head h3 {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
}

.task-list {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 8px;
}

.task-item {
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.task-item:hover {
  background: var(--bg-muted);
}

.task-item.active {
  background: var(--accent-soft);
  border-color: rgba(99, 102, 241, 0.25);
}

.task-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.task-item-id {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--accent);
}

.task-item-title {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.35;
  margin-bottom: 4px;
}

.task-item-step {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
}

.detail-breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.step-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.detail-header h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.stepper {
  display: flex;
  gap: 0;
  margin-bottom: 28px;
  padding: 16px 20px;
  background: var(--bg-muted);
  border-radius: var(--radius-md);
  overflow-x: auto;
}

.stepper-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
  min-width: 90px;
  cursor: pointer;
}

.stepper-item:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 14px;
  left: calc(50% + 16px);
  width: calc(100% - 32px);
  height: 2px;
  background: var(--border);
}

.stepper-item.done:not(:last-child)::after {
  background: var(--accent);
}

.stepper-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--border);
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 700;
  display: grid;
  place-items: center;
  position: relative;
  z-index: 1;
}

.stepper-item.active .stepper-dot {
  background: var(--c);
  color: #fff;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2);
}

.stepper-item.done .stepper-dot {
  background: var(--accent);
  color: #fff;
}

.stepper-label {
  font-size: 0.6875rem;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.3;
}

.stepper-item.active .stepper-label {
  color: var(--text-primary);
  font-weight: 600;
}

.alert-block {
  margin-bottom: 20px;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.inline-form {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.subtask-list {
  margin-top: 16px;
  display: grid;
  gap: 8px;
}

.subtask-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.diff-code {
  max-height: 320px;
  overflow: auto;
}

.diff-block {
  margin-bottom: 12px;
}

.diff-file {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 6px;
  font-family: var(--font-mono);
}

.terminal-wrap .terminal {
  max-height: 280px;
  margin: 0;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.terminal-wrap .terminal-header {
  background: #161b22;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  margin-bottom: 0;
  padding: 10px 16px;
}

.empty-panel {
  min-height: 400px;
  display: grid;
  place-items: center;
}

.review-hint {
  margin: 10px 0 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.stepper-item.clickable:hover .stepper-dot {
  transform: scale(1.08);
}

.stepper-item:hover .stepper-label {
  color: var(--text-primary);
}

.stepper-runs {
  font-size: 0.625rem;
  color: var(--text-muted);
}

.opinion-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.history-block {
  background: var(--bg-muted);
  border-radius: var(--radius-md);
  padding: 16px 20px;
}

.history-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.history-head .section-title {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.run-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.history-section {
  margin-bottom: 16px;
}

.history-section h5 {
  margin: 0 0 8px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.history-pre {
  margin: 0;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
  font-size: 0.8125rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.history-subtasks {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.history-subtasks li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
}

.auto-review-issues {
  margin: 8px 0 0;
  padding-left: 18px;
}

.audit-block {
  padding-top: 0;
  border-top: none;
  margin-bottom: 16px;
}

.audit-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.audit-list li {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 0.8125rem;
  padding: 8px 12px;
  background: var(--bg-muted);
  border-radius: 8px;
}

.audit-action {
  font-weight: 600;
  color: var(--accent);
}

.audit-user {
  color: var(--text-primary);
}

.audit-time {
  color: var(--text-muted);
}
</style>
