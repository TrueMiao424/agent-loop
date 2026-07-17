<template>
  <div class="page-card">
    <div class="page-header">
      <div>
        <h2>执行终端</h2>
        <p>所有任务的 Agent 执行日志汇总</p>
      </div>
    </div>

    <div class="terminal-wrap">
      <div class="terminal-header">
        <span class="terminal-dot red" />
        <span class="terminal-dot yellow" />
        <span class="terminal-dot green" />
        <span class="terminal-title">sandbox-terminal — all tasks</span>
      </div>
      <pre class="terminal mono">{{ combinedLogs || '暂无日志，提交需求后 Agent 执行日志将显示在这里...' }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const combinedLogs = computed(() =>
  store.tasks.map((t) => `=== Task #${t.id} ${t.title} ===\n${t.executionLogs || '(empty)'}`).join('\n\n'),
)
</script>

<style scoped>
.terminal-wrap .terminal {
  min-height: 480px;
  margin: 0;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.terminal-wrap .terminal-header {
  background: #161b22;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  margin-bottom: 0;
  padding: 10px 16px;
}
</style>
