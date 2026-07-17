<template>
  <div class="page-card">
    <div class="page-header">
      <div>
        <h2>协作消息</h2>
        <p>飞书群聊与系统通知记录</p>
      </div>
      <el-tag round>{{ store.webhookTotal }} 条消息</el-tag>
    </div>

    <div v-if="store.webhooks.length" class="message-list">
      <div v-for="m in store.webhooks" :key="m.id" class="message-item">
        <div class="message-avatar" :class="{ system: !m.isHuman }">
          {{ avatarText(m) }}
        </div>
        <div class="message-body">
          <div class="message-meta">
            <strong>{{ m.senderName || 'System' }}</strong>
            <span class="message-title">{{ m.title }}</span>
            <span class="message-time">{{ m.timestamp }}</span>
          </div>
          <div class="message-content">{{ m.message }}</div>
        </div>
      </div>
    </div>
    <el-empty v-else description="暂无协作消息" />

    <div v-if="store.webhookTotal > 0" class="pager">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="store.webhookTotal"
        :current-page="store.webhookPage"
        :page-size="store.webhookPageSize"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import type { WebhookMessage } from '@/types'

const store = useAppStore()

function avatarText(m: WebhookMessage) {
  const name = m.senderName || 'S'
  return name.charAt(0).toUpperCase()
}

async function onPageChange(page: number) {
  await store.setWebhookPage(page)
}

async function onSizeChange(size: number) {
  await store.setWebhookPage(1, size)
}
</script>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-item {
  display: flex;
  gap: 14px;
  padding: 16px;
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.message-item:hover {
  background: var(--bg-muted);
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-weight: 700;
  font-size: 0.875rem;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.message-avatar.system {
  background: linear-gradient(135deg, #64748b, #94a3b8);
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.message-meta strong {
  font-size: 0.875rem;
}

.message-title {
  font-size: 0.75rem;
  padding: 2px 8px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 999px;
  font-weight: 500;
}

.message-time {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: auto;
}

.message-content {
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
</style>
