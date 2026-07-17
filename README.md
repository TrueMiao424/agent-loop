# Agent Loop Platform

Web 端 **Claude Code 需求分发与 Agent Loop 编排系统**（Vue 3 + Django + MySQL）。

基于 `agent-task-manager-private` 的业务流程重构，提供从提需求到自动开发、人工 Review、测试与 Git 提交的完整闭环。

## 功能概览

- 用户注册 / 登录（JWT + Token 刷新）
- 业务提需求 → PM Agent 拆解 → 人工 Review 1 → Coding Agent → 人工 Review 2 → 自动测试部署
- 飞书群消息接入（Webhook / 长连接状态）
- 双槽并发 Session 守护（最多 2 个 Agent 进程）
- **中断提示 + checkpoint 续做**
- Redis 用户 Session 缓存；限流 / 熔断 / Prometheus / Celery 可选
- MySQL 连接池 + 日志落盘 `backend/logs/`
- Review2 后 **真实 apply diff + CI + git commit**

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| 后端 | Django 4 + DRF + JWT |
| 数据库 | MySQL 8（连接池） |
| 缓存 | Redis 7 |

## 工程分层

```
backend/apps/{module}/
  controller/   # 请求入口，参数校验
  service/      # 核心业务逻辑
  dao/          # 数据库 CRUD
  entity/       # ORM 模型
  dto/          # 序列化 / 入参出参
  client/       # 外部调用（Feishu / Anthropic / CI）
```

## 快速启动

### 1. 启动基础设施

```bash
cd e:/work/agent-loop-platform
docker compose up -d
copy .env.example .env
```

> **Docker 端口**：MySQL 映射 **3307→3306**，Redis 映射 **6380→6379**。  
> 使用 docker 时请在 `.env` 中设置 `DB_PORT=3307`、`REDIS_URL=redis://127.0.0.1:6380/0`。  
> 本机直接跑 MySQL/Redis 则用默认 3306 / 6379。

### 2. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8000
```

演示账号：`admin` / `admin123`（也可在登录页 **立即注册** 创建新账号）

**Agent 配置（必做）**：登录后进入 **配置管理**，填写 Anthropic API Key。系统默认 **优先使用 API Key**（`AGENT_PREFER_ANTHROPIC_API=true`），未配置时无法自动开发。

可选环境变量见 `.env.example`：`DEPLOY_HOOK_SCRIPT`（发布脚本）、`AGENT_REQUIRE_REAL_LLM`、`CI_STRICT` 等。

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173（若端口被占用，Vite 会自动尝试 5174、5175…，**以终端里 `Local:` 那一行的地址为准**）

> 同时请确保后端已启动：`python manage.py runserver 8000`

## 文档

- [用户手册](docs/USER_MANUAL.md)
- [飞书机器人配置全过程](docs/FEISHU_BOT_SETUP.md)
- [飞书协作指令](docs/FEISHU_COMMANDS.md)
- [代码规范](docs/CODE_STANDARDS.md)
- [架构说明](docs/ARCHITECTURE.md)
- [快速测试](docs/QUICK_TEST.md)

## 与原项目关系

| 原项目 (React + Python SQLite) | 新项目 |
|-------------------------------|--------|
| 5 步任务状态机 | 完整保留 |
| `/api/tasks/review1|review2` | 兼容 API 路径 |
| 飞书 Webhook 模拟 | FeishuClient + 消息表 |
| Claude Code 模拟 | Anthropic API + 可选 CLI |
| 无分层 / 无连接池 | Django 分层 + MySQL 连接池 |
| 无登录 | JWT + 注册登录 + Redis 缓存 |
| 无续做 | interrupt/resume + checkpoint |
