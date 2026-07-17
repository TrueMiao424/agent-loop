# 快速功能测试示例

> 5～10 分钟走通：提需求 → PM 拆解 → Review → 自动开发 → Review → 发布

## 0. 前置条件

```powershell
# 终端 1 - 后端
cd e:\work\agent-loop-platform\backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver 8000

# 终端 2 - 前端
cd e:\work\agent-loop-platform
npm run dev
```

首次使用或数据库为空时：

```powershell
cd backend
python manage.py migrate
python manage.py seed_demo
python manage.py seed_sample_task
```

- 登录：http://localhost:5173/login
- 注册：http://localhost:5173/register
- 演示账号：`admin` / `admin123`

---

## 1. 一键示例任务

运行 `seed_sample_task` 后会创建 **2 条示例需求**：

| 任务 | 阶段 | 你可以测什么 |
|------|------|-------------|
| 示例：登录页增加「记住我」 | 人工 Review 1 | 立刻点「同意动工」，不用等 Agent |
| 示例：看板任务卡片显示负责人 | 需求拆解 (Init) | 等 3～5 秒，调度器自动跑 PM Agent |

### 操作步骤

1. 登录后，顶部选择项目 **Agent Loop Demo**
2. 打开 **需求看板** → 应看到 2 张卡片
3. 点击 **「示例：登录页增加记住我」** → 进入工作台
4. 确认文件列表 → 点 **同意动工**
5. 回到看板，等任务进入 **自动开发** → **人工 Review 2**
6. 在工作台查看模拟 diff → 点 **合并发布**
7. 任务进入 **提交发布**，约 2 秒后变为 **已完成**

第二条任务会自动从「需求拆解」开始，可在 **执行终端** 看 PM Agent 日志。

---

## 2. 手动新建需求（完整流程）

在 **需求看板** → **新建需求**，粘贴以下内容：

**标题：**

```
Web 端增加深色模式切换
```

**验收标准 (PRD)：**

```
## 背景
用户反馈夜间使用界面过亮，需要深色模式。

## 验收标准
1. 顶栏增加「深色/浅色」切换按钮
2. 切换后全局 CSS 变量立即生效，刷新后保持用户选择
3. 默认跟随系统 prefers-color-scheme
4. 登录页同样支持深色模式
```

提交后：

1. 看板「需求拆解」列出现新卡片，状态 **待处理**
2. 约 3 秒内调度器拉起 PM Agent（**需先在配置管理填写 Anthropic API Key**）
3. 任务移到 **人工 Review 1** → 工作台手动点「同意动工」（日志会记录 Review 审计）
4. 自动开发 → **人工 Review 2** 点「合并发布」→ apply / CI / git commit

---

## 3. 测试中断 / 续做

1. 在 **自动开发** 阶段（状态 **执行中**）进入工作台
2. 点 **中断** → 任务变 **已中断**，顶部出现黄色续做条
3. 点 **续做** → 任务重新进入调度队列

---

## 4. 测试飞书 Webhook（可选）

模拟飞书群消息创建任务：

```powershell
curl -X POST http://127.0.0.1:8000/api/feishu/webhook/ ^
  -H "Content-Type: application/json" ^
  -d "{\"event\":{\"message\":{\"chat_id\":\"oc_demo_group_001\",\"content\":\"{\\\"text\\\":\\\"需求：做一个简单的 hello world API\\\"}\"}}}"
```

然后打开 **协作消息** 页查看记录；**需求看板** 会出现新任务。

> `oc_demo_group_001` 是 seed_demo 里 demo 项目的 chat_id，必须匹配才会建任务。

---

## 5. API 快速验证（可选）

```powershell
# 注册新用户（可选）
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/api/auth/register/" `
  -ContentType "application/json" `
  -Body '{"username":"demo_user","password":"demo123456","display_name":"Demo"}'

# 登录拿 token
$resp = Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/api/auth/login/" `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'
$token = $resp.data.access

# 列出项目
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/projects/" `
  -Headers @{ Authorization = "Bearer $token" }

# 列出任务（projectId=1 一般为 demo 项目）
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/tasks/?projectId=1" `
  -Headers @{ Authorization = "Bearer $token" }
```

---

## 6. 预期 vs 真实能力

| 功能 | 测试预期 |
|------|----------|
| 注册 / 登录 / JWT 刷新 | ✅ 真实，用户写入 MySQL |
| 项目 / 任务 CRUD | ✅ 真实，数据在 MySQL |
| 看板 / 工作台 / 消息列表 | ✅ 真实 API + 数据库 |
| PM 拆解 / 代码 diff | ✅ Anthropic API（配置管理页 Key，优先于 CLI） |
| Review 1 / 2 | ✅ 必须手动点击；执行日志 + reviewAudit 记录操作人 |
| apply diff / git commit | ✅ 真实写入项目目录并 commit |
| CI | ✅ 真实 npm/pytest（开发环境 `CI_STRICT=false` 可放宽） |
| 远程 deploy | ⚠️ 需配置 `DEPLOY_HOOK_SCRIPT`，否则仅本地 commit |
| Agent 来源标识 | ✅ 完成后仍保留 `agentMeta`（Anthropic API / CLI） |

---

## 7. 常见问题

**看板为空？**  
确认顶部已选项目；运行 `python manage.py seed_sample_task`。

**任务一直 Init？**  
后端必须运行（8000 端口）；Session 槽位满（2/2）时需等或去 **控制台** 重置会话。

**登录报 ECONNREFUSED？**  
先启动 `python manage.py runserver 8000`。
