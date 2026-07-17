<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="orb orb-1" />
      <div class="orb orb-2" />
      <div class="orb orb-3" />
    </div>

    <div class="login-content">
      <div class="login-hero">
        <div class="hero-badge">
          <el-icon :size="14"><Cpu /></el-icon>
          Agent Loop Platform
        </div>
        <h1>AI 驱动的<br />需求分发与编排</h1>
        <p>业务提需求 → Agent 自动开发 → 人工 Review → 自动部署上线</p>
        <ul class="feature-list">
          <li><el-icon><Check /></el-icon> PM Agent 需求拆解</li>
          <li><el-icon><Check /></el-icon> Claude Code 自动编码</li>
          <li><el-icon><Check /></el-icon> 双节点人工 Review</li>
          <li><el-icon><Check /></el-icon> 中断续做 & 飞书协作</li>
        </ul>
      </div>

      <div class="login-card">
        <h2>欢迎回来</h2>
        <p class="subtitle">登录以管理 Agent 任务与工作流</p>
        <el-form @submit.prevent="onSubmit" size="large">
          <el-form-item>
            <el-input v-model="username" placeholder="用户名" :prefix-icon="User" />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="password"
              type="password"
              placeholder="密码"
              show-password
              :prefix-icon="Lock"
            />
          </el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" class="submit-btn" round>
            登录
          </el-button>
        </el-form>
        <p class="hint">
          还没有账号？
          <router-link to="/register">立即注册</router-link>
          · 演示账号 admin / admin123
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Check, Cpu, Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('admin')
const password = ref('admin123')
const loading = ref(false)

async function onSubmit() {
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/kanban')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  position: relative;
  overflow: hidden;
  background: #0f172a;
}

.login-bg {
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

.login-content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 64px;
  max-width: 960px;
  width: 100%;
  align-items: center;
}

.login-hero {
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

.login-hero h1 {
  margin: 0;
  font-size: 2.75rem;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.03em;
}

.login-hero > p {
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

.login-card {
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 36px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.3);
}

.login-card h2 {
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
  .login-content {
    grid-template-columns: 1fr;
    max-width: 420px;
  }

  .login-hero {
    text-align: center;
  }

  .login-hero h1 {
    font-size: 2rem;
  }

  .feature-list {
    display: none;
  }
}
</style>
