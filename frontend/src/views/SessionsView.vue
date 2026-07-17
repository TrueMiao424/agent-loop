<template>
  <div class="page-card">
    <div class="page-header">
      <div>
        <h2>控制台 & 进程</h2>
        <p>Agent Session 并发槽位监控（最大 {{ store.maxConcurrentSessions }} 个）</p>
      </div>
      <div class="page-header-actions">
        <div class="slot-indicator">
          <span
            v-for="i in store.maxConcurrentSessions"
            :key="i"
            class="slot"
            :class="{ filled: i <= store.sessionProcessingCount }"
          />
          <span class="slot-text">
            {{ store.sessionProcessingCount }}/{{ store.maxConcurrentSessions }} 槽位占用
          </span>
        </div>
        <el-button type="danger" plain round @click="reset">重置全部会话</el-button>
      </div>
    </div>

    <el-table :data="store.sessions" style="width: 100%" stripe empty-text="暂无 Session">
      <el-table-column prop="sessionId" label="Session ID" min-width="180">
        <template #default="{ row }">
          <span class="mono session-id">{{ row.sessionId }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="taskId" label="Task" width="80" align="center" />
      <el-table-column prop="pid" label="PID" width="90" align="center">
        <template #default="{ row }">
          <span class="mono">{{ row.pid }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="projectName" label="项目" min-width="120" />
      <el-table-column prop="commandLine" label="Command" min-width="200">
        <template #default="{ row }">
          <code class="cmd">{{ row.commandLine }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120" align="center">
        <template #default="{ row }">
          <span :class="['status-badge', sessionStatusClass(row.status)]">{{ row.status }}</span>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="store.sessionTotal > 0" class="pager">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="store.sessionTotal"
        :current-page="store.sessionPage"
        :page-size="store.sessionPageSize"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { sessionApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useAppStore()

function sessionStatusClass(status: string) {
  const map: Record<string, string> = {
    Processing: 'status-processing',
    Finished: 'status-finished',
    Failed: 'status-failed',
    Interrupted: 'status-interrupted',
  }
  return map[status] || 'status-init'
}

async function onPageChange(page: number) {
  await store.setSessionPage(page)
}

async function onSizeChange(size: number) {
  await store.setSessionPage(1, size)
}

async function reset() {
  await ElMessageBox.confirm('确认重置所有 CMD 会话？此操作不可撤销。', '警告', { type: 'warning' })
  await sessionApi.reset()
  ElMessage.success('已重置')
  await store.setSessionPage(1)
  await store.refreshAll()
}
</script>

<style scoped>
.slot-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: var(--bg-muted);
  border-radius: 999px;
}

.slot {
  width: 12px;
  height: 12px;
  border-radius: 4px;
  background: var(--border);
  transition: background 0.2s ease;
}

.slot.filled {
  background: var(--accent);
}

.slot-text {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-left: 4px;
}

.session-id {
  font-size: 0.8125rem;
  color: var(--accent);
}

.cmd {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-secondary);
  background: var(--bg-muted);
  padding: 2px 8px;
  border-radius: 4px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
</style>
