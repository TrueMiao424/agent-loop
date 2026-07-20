<template>
  <div class="page-card settings">
    <div class="page-header">
      <div>
        <h2>配置管理</h2>
        <p>每位登录用户独立配置 Agent LLM；任务创建与执行将使用创建者自己的 Key</p>
      </div>
      <div class="page-header-actions">
        <el-button round :loading="testing" @click="testConnection">测试连接</el-button>
        <el-button type="primary" round :loading="saving" @click="save">保存配置</el-button>
      </div>
    </div>

    <el-form v-if="form" v-loading="loading" label-position="top">
      <!-- Agent LLM -->
      <div class="config-section">
        <div class="config-section-head">
          <el-icon :size="20" color="#6366f1"><Cpu /></el-icon>
          <div class="head-text">
            <div class="head-row">
              <h3>Agent LLM（Anthropic）</h3>
              <el-tag v-if="form.AGENT_LLM.hasApiKey" type="success" size="small" round>已配置</el-tag>
              <el-tag v-else type="info" size="small" round>未配置</el-tag>
              <el-tag v-if="form.AGENT_LLM.source === 'env_migrated'" size="small" round effect="plain">已从 .env 迁移</el-tag>
              <el-tag v-else-if="form.AGENT_LLM.source === 'user'" size="small" round effect="plain">当前用户</el-tag>
            </div>
            <p>PM 拆解、Coding Agent 使用您账号下的 Key。留空 API Key 则保持原值不变。</p>
          </div>
        </div>

        <div class="config-grid">
          <el-form-item label="API Key">
            <el-input
              v-model="form.AGENT_LLM.apiKey"
              type="password"
              show-password
              :placeholder="form.AGENT_LLM.hasApiKey ? `已保存 ${form.AGENT_LLM.apiKeyMasked}` : 'sk-...'"
            />
          </el-form-item>
          <el-form-item label="模型">
            <el-input v-model="form.AGENT_LLM.model" placeholder="claude-sonnet-4-6" />
          </el-form-item>
          <el-form-item label="Base URL" class="span-2">
            <el-input v-model="form.AGENT_LLM.baseUrl" placeholder="http://47.95.9.5:8000 或 https://api.anthropic.com" />
          </el-form-item>
        </div>
      </div>

      <!-- Feishu -->
      <div class="config-section">
        <div class="config-section-head">
          <el-icon :size="20" color="#10b981"><ChatDotRound /></el-icon>
          <div class="head-text">
            <div class="head-row">
              <h3>飞书集成</h3>
              <el-tag v-if="form.FEISHU.hasAppSecret" type="success" size="small" round>已配置</el-tag>
              <el-tag v-else type="info" size="small" round>未配置</el-tag>
            </div>
            <p>
              配置飞书应用凭证与 WebSocket 长连接。创建应用、赋权、发版须在
              <a href="https://open.feishu.cn/app" target="_blank" rel="noopener">飞书开放平台</a>
              人工完成。详见文档
              <code>docs/FEISHU_BOT_SETUP.md</code>。
            </p>
          </div>
        </div>

        <div class="config-grid">
          <el-form-item label="App ID">
            <el-input v-model="form.FEISHU.appId" placeholder="cli_xxx" />
          </el-form-item>
          <el-form-item label="App Secret">
            <el-input
              v-model="form.FEISHU.appSecret"
              type="password"
              show-password
              :placeholder="form.FEISHU.hasAppSecret ? `已保存 ${form.FEISHU.appSecretMasked}` : '留空则不修改'"
            />
          </el-form-item>
          <el-form-item label="WebSocket 长连接">
            <el-switch v-model="form.FEISHU.wsEnabled" active-text="开启" inactive-text="关闭" />
          </el-form-item>
          <el-form-item label="群聊需 @ 机器人">
            <el-switch
              v-model="form.FEISHU.requireMention"
              :disabled="!form.FEISHU.wsEnabled"
              active-text="是"
              inactive-text="否"
            />
            <p v-if="form.FEISHU.requireMention" class="field-hint warn">
              开启后，群里发消息必须 @ 机器人，否则会被忽略（长连接日志会显示「被过滤」）。
            </p>
          </el-form-item>
          <el-form-item label="关联项目">
            <el-select v-model="form.FEISHU.defaultProjectId" placeholder="选择接收群消息的项目" clearable>
              <el-option v-for="p in projects" :key="p.id" :label="p.projectName" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="飞书群 chat_id" class="span-2">
            <div class="chat-id-row">
              <el-input v-model="form.FEISHU.chatGroupId" placeholder="oc_xxx" />
              <el-button round :loading="feishuChatsLoading" @click="loadFeishuChats">获取群列表</el-button>
            </div>
            <p v-if="feishuChats.length" class="field-hint">
              机器人已加入的群（点击选用）：
              <el-button
                v-for="chat in feishuChats"
                :key="chat.chatId"
                link
                type="primary"
                @click="selectFeishuChat(chat.chatId)"
              >
                {{ chat.name }} ({{ chat.chatId }})
              </el-button>
            </p>
            <p v-else class="field-hint">
              先把机器人拉进目标群，保存凭证后点「获取群列表」选用；需开通 im:chat。
            </p>
          </el-form-item>
        </div>

        <div v-if="feishuStatus" class="feishu-ws-block">
          <div class="feishu-ws-head">
            <span>长连接状态</span>
            <el-tag :type="feishuStatusTag" size="small" round>{{ feishuStatusLabel }}</el-tag>
            <el-button size="small" round :loading="feishuRefreshing" @click="loadFeishuStatus">刷新</el-button>
            <el-button size="small" type="primary" round :loading="feishuRestarting" @click="restartFeishuWs">
              重新连接
            </el-button>
          </div>
          <p class="feishu-ws-hint">
            开启 WebSocket 长连接后，后端可直接接收飞书群消息（无需公网 webhook）。
            修改 App 凭证后点「重新连接」即可生效，无需重启后端。
            若开启了「群聊需 @ 机器人」，请在群里 @ 机器人发消息，否则消息会被过滤。
          </p>
          <p v-if="feishuStatus.error" class="feishu-ws-error">{{ feishuStatus.error }}</p>
          <pre v-if="feishuLogs.length" class="feishu-ws-logs">{{ feishuLogs.join('\n') }}</pre>
        </div>
      </div>
    </el-form>
    <div v-else-if="loading" v-loading="true" class="settings-loading" />
    <el-empty v-else description="配置加载失败，请刷新重试" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ChatDotRound, Cpu } from '@element-plus/icons-vue'
import { feishuApi, projectApi, settingsApi } from '@/api'
import { ElMessage } from 'element-plus'
import type { Project } from '@/types'

interface AgentLlmConfig {
  apiKey: string
  apiKeyMasked: string
  hasApiKey: boolean
  baseUrl: string
  model: string
  source: string
}

interface FeishuConfig {
  appId: string
  appSecret: string
  appSecretMasked: string
  hasAppSecret: boolean
  wsEnabled: boolean
  requireMention: boolean
  chatGroupId: string
  defaultProjectId: number | null
}

interface SettingsForm {
  AGENT_LLM: AgentLlmConfig
  FEISHU: FeishuConfig
}

const form = ref<SettingsForm | null>(null)
const projects = ref<Project[]>([])
const saving = ref(false)
const testing = ref(false)
const loading = ref(false)
const feishuStatus = ref<{
  enabled: boolean
  status: string
  error?: string
} | null>(null)
const feishuLogs = ref<string[]>([])
const feishuRefreshing = ref(false)
const feishuRestarting = ref(false)
const feishuChatsLoading = ref(false)
const feishuChats = ref<Array<{ chatId: string; name: string; description?: string }>>([])

const feishuStatusLabel = computed(() => {
  const s = feishuStatus.value?.status || 'UNKNOWN'
  const map: Record<string, string> = {
    CONNECTED: '已连接',
    CONNECTING: '连接中',
    DISABLED: '未启用',
    NOT_CONFIGURED: '未配置',
    ERROR: '异常',
    STOPPED: '未启动',
  }
  return map[s] || s
})

const feishuStatusTag = computed(() => {
  const s = feishuStatus.value?.status
  if (s === 'CONNECTED') return 'success'
  if (s === 'CONNECTING') return 'warning'
  if (s === 'DISABLED') return 'info'
  return 'danger'
})

async function loadFeishuStatus() {
  feishuRefreshing.value = true
  try {
    feishuStatus.value = await feishuApi.status()
    feishuLogs.value = await feishuApi.logs()
  } catch {
    feishuStatus.value = null
  } finally {
    feishuRefreshing.value = false
  }
}

async function loadFeishuChats() {
  feishuChatsLoading.value = true
  try {
    feishuChats.value = await feishuApi.chats()
    if (!feishuChats.value.length) {
      ElMessage.warning('未找到机器人所在的群，请先把机器人拉进群后再试')
    }
  } catch (e: any) {
    feishuChats.value = []
    ElMessage.error(e?.msg || e?.message || '获取群列表失败')
  } finally {
    feishuChatsLoading.value = false
  }
}

function selectFeishuChat(chatId: string) {
  if (!form.value) return
  form.value.FEISHU.chatGroupId = chatId
  ElMessage.success(`已填入 chat_id：${chatId}`)
}

async function restartFeishuWs() {
  feishuRestarting.value = true
  try {
    await feishuApi.restart()
    ElMessage.success('长连接已重新连接')
    await loadFeishuStatus()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || '重连失败')
  } finally {
    feishuRestarting.value = false
  }
}

async function loadProjects() {
  try {
    projects.value = await projectApi.list()
  } catch {
    projects.value = []
  }
}

async function load() {
  loading.value = true
  try {
    form.value = await settingsApi.get()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || '加载配置失败')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form.value) return
  if (form.value.FEISHU.chatGroupId && !form.value.FEISHU.defaultProjectId) {
    ElMessage.warning('请同时选择关联项目，否则无法匹配飞书群消息')
    return
  }
  saving.value = true
  try {
    await settingsApi.save({
      AGENT_LLM: {
        apiKey: form.value.AGENT_LLM.apiKey,
        baseUrl: form.value.AGENT_LLM.baseUrl,
        model: form.value.AGENT_LLM.model,
      },
      FEISHU: {
        appId: form.value.FEISHU.appId,
        appSecret: form.value.FEISHU.appSecret,
        wsEnabled: form.value.FEISHU.wsEnabled,
        requireMention: form.value.FEISHU.requireMention,
        chatGroupId: form.value.FEISHU.chatGroupId,
        defaultProjectId: form.value.FEISHU.defaultProjectId,
      },
    })
    ElMessage.success('配置已保存')
    await load()
    await loadFeishuStatus()
    form.value!.AGENT_LLM.apiKey = ''
    form.value!.FEISHU.appSecret = ''
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  try {
    const res = await settingsApi.test()
    ElMessage.success(`连接成功：${res.reply || res.model}`)
  } catch (e: any) {
    const msg = e?.msg || e?.message || '连接失败'
    if (String(msg).includes('timeout')) {
      ElMessage.error('连接超时，请检查 Base URL 与网络；代理较慢时可多等片刻后重试')
    }
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadProjects()
  load()
  loadFeishuStatus()
})
</script>

<style scoped>
.settings-loading {
  min-height: 200px;
}

.config-section {
  padding-bottom: 24px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}

.config-section-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 20px;
}

.head-text {
  flex: 1;
}

.head-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.config-section-head h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.config-section-head p {
  margin: 6px 0 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 24px;
}

.config-grid :deep(.el-select) {
  width: 100%;
}

.span-2 {
  grid-column: 1 / -1;
}

.chat-id-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.chat-id-row .el-input {
  flex: 1;
}

.field-hint {
  margin: 8px 0 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.field-hint code {
  font-size: 0.75rem;
  word-break: break-all;
}

.field-hint.warn {
  color: #d97706;
}

.feishu-ws-block {
  margin-top: 16px;
  padding: 14px 16px;
  background: var(--bg-muted);
  border-radius: var(--radius-md);
}

.feishu-ws-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 0.875rem;
  font-weight: 600;
}

.feishu-ws-hint {
  margin: 0 0 8px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.feishu-ws-error {
  margin: 0 0 8px;
  color: #ef4444;
  font-size: 0.8125rem;
}

.feishu-ws-logs {
  margin: 0;
  max-height: 160px;
  overflow: auto;
  padding: 10px 12px;
  background: #161b22;
  color: #c9d1d9;
  border-radius: 8px;
  font-size: 0.75rem;
  line-height: 1.4;
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
  .span-2 {
    grid-column: auto;
  }
}
</style>
