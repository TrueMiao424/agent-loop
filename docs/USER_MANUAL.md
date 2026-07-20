# 用户手册

## 1. 系统简介

Agent Loop Platform：Web/飞书提需求 → PM 拆解 → Review 1 → Coding → Review 2 → **真实写码 + 自测 + Git 提交**。

## 2. 环境准备

```bash
docker compose up -d   # 或本机 MySQL + Redis(6379)
cd backend && pip install -r requirements.txt
python manage.py migrate && python manage.py seed_demo
python manage.py runserver 8000
npm run dev   # 项目根目录
```

## 3. 账号

### 注册与登录

- 打开前端 **登录页** → 点击 **立即注册**，填写用户名（≥3 字符）、密码（≥6 位）与可选显示名
- 注册成功后自动登录并进入看板
- 演示环境可使用 `admin` / `admin123`

### 每人 API Key

**配置管理** → 填写 Key / Base URL / 模型 → 测试连接 → 保存。

### Git / CI（`.env`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `GIT_AUTO_INIT` | true | 项目路径无 git 时自动 init |
| `GIT_PUSH_ENABLED` | false | true 时 commit 后 push 到 origin |
| `GIT_DEFAULT_BRANCH` | main | 推送分支 |

### Celery（可选）

```env
USE_CELERY=true
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

另开终端：`celery -A config worker -l info`

### 飞书

完整步骤见 [飞书机器人配置全过程](./FEISHU_BOT_SETUP.md)。简述：开放平台创建应用 → 开通机器人与权限 → 事件订阅优先用**长连接** → 配置管理填写 App ID/Secret 并开启长连接 → 把机器人拉进群并用「获取群列表」填入 chat_id。指令见 [FEISHU_COMMANDS.md](./FEISHU_COMMANDS.md)。

## 4. 工作流

1. 看板新建需求（需已配 Key）
2. PM 自动拆解 → **Review 1** 确认文件
3. Coding 生成 diff → **Review 2** 审查
4. 合并发布：**写入项目目录 → npm/pytest 自测 → git commit（可选 push）**

项目 **代码路径** 须为真实本地仓库路径。

## 5. 中断与续做

工作台 **中断**（确认弹窗）→ 状态 `Interrupted` → **续做** 立即重新调度。

## 6. 日志与监控

- 控制台 + 文件：`backend/logs/agent_loop.log`
- Prometheus：`GET /api/metrics/`
- 每条 API 带 TraceID，便于排查

## 7. 常见问题

**Q: Redis 连接失败？**  
A: 本机 Redis 默认 6379，确认 `.env` 中 `REDIS_URL=redis://127.0.0.1:6379/0`。

**Q: Git commit 失败？**  
A: 检查项目代码路径是否存在；必要时设置 `GIT_AUTO_INIT=true`。

**Q: 不想 push 到远程？**  
A: 保持 `GIT_PUSH_ENABLED=false`，仅本地 commit。

**Q: Celery 任务不执行？**  
A: 确认 `USE_CELERY=true` 且 worker 已启动。
