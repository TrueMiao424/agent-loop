<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="orb orb-1" />
      <div class="orb orb-2" />
      <div class="orb orb-3" />
    </div>

    <div class="auth-content">
      <div class="auth-hero">
        <div class="hero-badge">
          <el-icon :size="14"><Cpu /></el-icon>
          Agent Loop Platform
        </div>
        <h1>创建账号<br />开始编排 Agent 任务</h1>
        <p>注册后可配置 API Key、创建项目并提交需求到自动化工作流</p>
        <ul class="feature-list">
          <li><el-icon><Check /></el-icon> 独立账号与 JWT 登录态</li>
          <li><el-icon><Check /></el-icon> 每人独立 Anthropic API Key</li>
          <li><el-icon><Check /></el-icon> 看板 + 工作台全流程</li>
          <li><el-icon><Check /></el-icon> 中断续做 & 协作消息</li>
        </ul>
      </div>

      <div class="auth-card">
        <h2>注册账号</h2>
        <p class="subtitle">填写信息后即可登录使用平台</p>
        <el-form @submit.prevent="onSubmit" size="large">
          <el-form-item>
            <el-input v-model="username" placeholder="用户名（至少 3 个字符）" :prefix-icon="User" />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="displayName"
              placeholder="显示名称（可选）"
              :prefix-icon="Postcard"
            />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="password"
              type="password"
              placeholder="密码（至少 6 位）"
              show-password
              :prefix-icon="Lock"
            />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="confirmPassword"
              type="password"
              placeholder="确认密码"
              show-password
              :prefix-icon="Lock"
            />
          </el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" class="submit-btn" round>
            注册并登录
          </el-button>
        </el-form>
        <p class="hint">
          已有账号？
          <router-link to="/login">返回登录</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Cpu, Lock, Postcard, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const displayName = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)

async function onSubmit() {
  const name = username.value.trim()
  if (name.length < 3) {
    ElMessage.warning('用户名至少 3 个字符')
    return
  }
  if (password.value.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (password.value !== confirmPassword.value) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  loading.value = true
  try {
    await auth.register(name, password.value, displayName.value.trim())
    ElMessage.success('注册成功')
    router.push('/kanban')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  position: relative;
  overflow: hidden;
  background: #0f172a;
}

.auth-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: #6366f1;
  top: -150px;
  right: -100px;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: #8b5cf6;
  bottom: -100px;
  left: -80px;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: #3b82f6;
  top: 50%;
  left: 40%;
  opacity: 0.3;
}

.auth-content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 64px;
  max-width: 960px;
  width: 100%;
  align-items: center;
}

.auth-hero {
  color: #f8fafc;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  font-size: 0.8125rem;
  color: #c7d2fe;
  margin-bottom: 24px;
}

.auth-hero h1 {
  margin: 0;
  font-size: 2.75rem;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.03em;
}

.auth-hero > p {
  margin: 20px 0 32px;
  font-size: 1.05rem;
  color: #94a3b8;
  line-height: 1.6;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.9375rem;
  color: #cbd5e1;
}

.feature-list .el-icon {
  color: #6366f1;
}

.auth-card {
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 36px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.3);
}

.auth-card h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.subtitle {
  margin: 8px 0 28px;
  color: #64748b;
  font-size: 0.875rem;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-weight: 600;
  margin-top: 8px;
}

.hint {
  margin: 20px 0 0;
  text-align: center;
  color: #94a3b8;
  font-size: 0.8125rem;
}

.hint a {
  color: #6366f1;
  text-decoration: none;
  font-weight: 600;
}

.hint a:hover {
  text-decoration: underline;
}

@media (max-width: 860px) {
  .auth-content {
    grid-template-columns: 1fr;
    max-width: 420px;
  }

  .auth-hero {
    text-align: center;
  }

  .auth-hero h1 {
    font-size: 2rem;
  }

  .feature-list {
    display: none;
  }
}
</style>
