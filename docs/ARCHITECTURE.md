# 架构说明

本文档描述 Agent Loop Platform 的整体架构、分层约定与高并发相关能力。

## 系统架构

```
┌─────────────┐     REST/JWT      ┌──────────────────────────────────┐
│  Vue 3 前端  │ ◄──────────────► │  Django + DRF                    │
│  看板/工作台  │                  │  controller → service → dao      │
└─────────────┘                  │         ↓                          │
                                 │  client (Anthropic / Feishu / CI) │
                                 └──────────┬───────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
               MySQL 8                 Redis 7                  项目仓库
            任务/用户/会话              缓存/锁/限流              apply + git
```

## 后端分层

| 目录 | 职责 |
|------|------|
| `controller/` | 参数校验、调用 Service、统一响应 |
| `service/` | 业务流程、状态机、事务边界 |
| `dao/` | ORM CRUD 封装 |
| `entity/` | Django Model |
| `dto/` | Serializer / 入参出参 |
| `client/` | 外部 HTTP / SDK（Anthropic、飞书、CI） |
| `common/service/` | Redis 缓存、Session、调度锁 |
| `common/middleware/` | TraceID、AccessLog、RateLimit |

## 核心能力

| 能力 | 实现 |
|------|------|
| 用户认证 | JWT 登录 / 注册 / refresh；Redis 缓存用户 profile |
| 任务状态机 | 5 步工作流 + Review 卡点 + checkpoint 续做 |
| Agent 调度 | 双槽 Session 守护 + 线程池 / Celery 可选 |
| 限流 | `RateLimitMiddleware` + Redis 滑动窗口 |
| 熔断 | `CircuitBreaker` 包裹 Anthropic / 飞书 |
| 幂等 | `X-Idempotency-Key` + `task_idempotency` |
| 可观测 | AccessLog + `@log_method` + Prometheus `/api/metrics/` |
| 日志落盘 | `backend/logs/agent_loop.log`（Rotating） |

## 业务工作流

| 阶段 | 行为 |
|------|------|
| PM 拆解 | Anthropic API 生成 `predicted_files` 与 `sub_tasks` |
| 自动开发 | Coding Agent 生成 `code_diffs` |
| Review 2 通过 | 进入 Commit Push |
| Commit Push | **真实** apply diff → CI 自测 → git commit（可选 push） |
| 飞书 | 配置 App ID/Secret 后真实发消息，否则 mock 日志 |

### Git 配置

| 环境变量 | 说明 |
|----------|------|
| `GIT_AUTO_INIT` | 项目目录无 `.git` 时自动 `git init` |
| `GIT_PUSH_ENABLED` | `true` 时执行 `git push origin` |
| `GIT_DEFAULT_BRANCH` | 默认 `main` |

项目的 **代码路径** 必须指向真实仓库目录。

## 运维

```bash
docker compose up -d
python manage.py runserver 8000
celery -A config worker -l info   # USE_CELERY=true 时
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/metrics/
```
