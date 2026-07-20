# 飞书机器人配置

本文按「开放平台每一项配置」说明如何把**企业自建应用机器人**接到 Agent Loop Platform。

完成后可实现：

- 群内固定指令：创建任务 / Review / 续做 / 取消任务（见 [FEISHU_COMMANDS.md](./FEISHU_COMMANDS.md)）
- 平台把 Review 摘要、自动 Review 建议、失败/中断提醒推回同一群

**强烈推荐：事件订阅使用「长连接」**（本机无需公网、无需填 Request URL）。  
HTTP 回调（Webhook）仅作有公网 HTTPS 时的备用方案。

官方参考（配置时对照开放平台最新文案）：

- [接收消息事件 `im.message.receive_v1`](https://open.feishu.cn/document/server-docs/im-v1/message/events/receive)
- [使用长连接接收事件](https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/request-url-configuration-case)
- [发送消息 API](https://open.feishu.cn/document/server-docs/im-v1/message/create)

---

## 0. 准备清单

| 项 | 说明 |
|----|------|
| 飞书租户 | 能创建「企业自建应用」，并能发布版本 / 配置可用范围 |
| Agent Loop 已跑通 | MySQL、Redis、后端 `8000`、前端 Vite |
| 项目 | 看板中至少 1 个项目（合法代码路径） |
| Anthropic Key | 配置管理页已填写，否则拆解/开发无法执行 |
| Python 依赖 | `lark-oapi`（`backend/requirements.txt` 已含） |

配置保存后：**改权限 / 改事件 / 改可用范围 → 必须在开放平台「创建版本并发布」才会对企业内生效。**

---

## 1. 创建企业自建应用

1. 打开 [飞书开放平台 - 我的应用](https://open.feishu.cn/app)
2. **创建企业自建应用** → 填写名称、描述、图标
3. 创建完成后，进入 **凭证与基础信息**，记录：

| 字段 | 示例 | 用途 |
|------|------|------|
| App ID | `cli_aade1d8b383a9bfc` | 平台配置 / `.env` `FEISHU_APP_ID` |
| App Secret | （点击查看/重置） | 平台配置 / `.env` `FEISHU_APP_SECRET` |

> App Secret 泄露需立即重置，并同步更新 Agent Loop 配置管理中的 Secret。

本平台还会用 App 凭证调用：

| 接口 | 用途 |
|------|------|
| `POST /open-apis/auth/v3/tenant_access_token/internal` | 获取 `tenant_access_token` |
| `POST /open-apis/im/v1/messages?receive_id_type=chat_id` | 向群发文本 |
| `GET /open-apis/im/v1/chats` | 配置页「获取群列表」 |
| `GET /open-apis/bot/v3/info` | 取机器人 `open_id`（用于「必须 @ 机器人」过滤） |

---

## 2. 添加应用能力：机器人（必做）

路径：**应用能力 → 添加应用能力 → 机器人**

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 机器人能力 | 已添加 | **未开启则无法收发 IM** |
| 机器人名称 | 与群内展示名一致 | 可按需改 |
| 描述 / 头像 | 可选 | — |

开启机器人后，仍需在后面「发布版本」才会对真实员工/群生效。

---

## 3. 权限管理（API 权限 · 应用身份）

路径：**开发配置 → 权限管理 → API 权限**（开通 **应用身份** 权限，不是用户身份）

按关键词搜索并开通下表。名称以开放平台当前文案为准；**Scope 一列可精确搜索。**

### 3.1 必开（本平台刚需）

| 作用 | 权限名称（常见文案） | Scope / 关键词 | 对应本系统能力 |
|------|----------------------|----------------|----------------|
| 群里收到 @ 机器人消息 | 获取群组中用户@机器人的消息 / 接收群聊中@机器人消息事件 | `im:message.group_at_msg:readonly` 或 `im:message.group_at_msg` | 订阅并处理群指令（推荐搭配「需 @」） |
| 单聊收到用户消息 | 读取用户发给机器人的单聊消息 | `im:message.p2p_msg:readonly` 或 `im:message.p2p_msg` | 可选；主要用群聊 |
| 机器人发消息 | 以应用的身份发消息 | `im:message:send_as_bot` | Review 推送、错误提示、创建成功回复 |
| 发消息（备选包） | 获取与发送单聊、群组消息 | `im:message` | 与上一项二选一或同时开均可 |
| 获取群列表 | 获取群组信息 / 获取用户或机器人所在的群列表 | `im:chat` / `im:chat:readonly` | 配置页「获取群列表」填 `chat_id` |
| 机器人信息 | 获取应用信息相关（随 bot/v3/info） | 搜索 `bot` / 应用信息 | 获取 bot `open_id`，供 @ 过滤 |

订阅事件 `im.message.receive_v1` 时，开放平台要求具备接收消息相关权限之一，详见官方文档「权限要求」列表（开启其中任一项即可订阅事件，但本系统群协作建议至少开 **group_at** + **send_as_bot**）。

### 3.2 建议按场景加开

| 场景 | 权限 | Scope 关键词 | 备注 |
|------|------|--------------|------|
| 不要求 @，群里任意用户消息都要进平台 | 获取群组中所有消息 | `im:message.group_msg` 或 `im:message.group_msg:readonly` | **敏感权限**，需审批；且平台侧「群聊需 @ 机器人」应关掉 |
| 需要更细的用户字段 | 获取用户 user ID 等 | `contact:user.employee_id:readonly` 等 | 本系统不依赖，可不申请 |

### 3.3 权限开通后必做

1. 权限列表显示 **已开通**
2. **版本管理与发布 → 创建版本 → 申请发布**（权限变更未发版 = 线上不生效）
3. **可用范围**：至少包含你自己 + 会发指令的同事（或按部门）

---

## 4. 事件与回调（核心）

路径：**开发配置 → 事件与回调**（有的控制台拆成「事件配置」「回调配置」）

本平台当前处理：

| 类型 | 标识 | 是否使用 |
|------|------|----------|
| 事件 | `im.message.receive_v1`（接收消息 v2.0） | **必须订阅** |
| 事件加密 / Encrypt Key | — | 长连接模式由 SDK 处理；HTTP 模式本仓库**未做** Encrypt Key 解密，**请勿开启加密推送**（或保持默认未加密） |
| 回调（卡片交互等） | 如 `card.action.trigger` | **不需要**（暂无消息卡片按钮） |
| URL 校验 Verification Token | HTTP 回调场景 | 见下文方式 B；长连接可不填到本平台 |

### 4.1 方式 A：长连接接收事件（推荐）

#### 开放平台侧

| 步骤 | 操作 |
|------|------|
| 1 | **事件与回调 → 事件配置 → 订阅方式** → 选择 **使用长连接接收事件** |
| 2 | **先启动本平台后端**并开启长连接（见第 6 节），状态为 `CONNECTED` |
| 3 | 回到开放平台点 **保存**（若提示「应用未建立长连接」，说明后端未连通，先查第 8 节） |
| 4 | **添加事件** → 搜索并勾选：**接收消息** / `im.message.receive_v1`（消息与群组） |
| 5 | 保存 → **创建版本并发布** |

长连接服务端点（平台内置，无需你填写）：

```text
wss://open.feishu.cn/open-apis/event/v1/outbound
```

约束（飞书官方）：

- 仅企业自建应用
- 收到事件后宜在约 3 秒内处理完（本平台在线程池处理业务，避免阻塞 WS）
- 同一应用多实例长连接为**集群模式**：随机一个客户端收消息 → **不要开两个后端同时连同一 App**

#### Agent Loop 侧（与开放平台对应）

| 配置位置 | 字段 | 值 |
|----------|------|-----|
| 配置管理 → 飞书集成 | WebSocket 长连接 | **开启** |
| `.env`（可选初始值） | `FEISHU_WS_ENABLED=true` | 与上一致 |
| 配置管理 | 群聊需 @ 机器人 | 见第 6.3 节 |

#### 回调配置页怎么填？

长连接模式下：

- **不必**填写「请求地址 Request URL」
- **回调配置**若与事件分开：保持关闭或空即可（无卡片回调）
- Verification Token / Encrypt Key：**可不写入本平台**（页面无此项）

### 4.2 方式 B：HTTP 将事件发送至开发者服务器（备用）

仅当有 **公网 HTTPS** 时使用。本地 `http://127.0.0.1:8000` **不能**直接填给飞书。

#### 开放平台侧明细

| 配置项 | 填写值 |
|--------|--------|
| 订阅方式 | **将事件发送至开发者服务器** |
| 请求地址 Request URL | `https://你的域名/api/feishu/webhook/` |
| 加密策略 | **不加密**（本仓库 HTTP 入口未实现 Encrypt Key 解密） |
| Verification Token | 开放平台自动生成；飞书用 challenge 校验时本接口返回 challenge（见下） |
| 已添加事件 | `im.message.receive_v1` |

#### URL 校验（challenge）

飞书首次保存 Request URL 时会 POST：

```json
{
  "challenge": "随机串",
  "token": "verification_token",
  "type": "url_verification"
}
```

本平台接口会 **裸返回**（注意不是包在 `data` 里）：

```json
{ "challenge": "随机串" }
```

实现位置：`POST /api/feishu/webhook/`（`AllowAny`，无需登录）。

#### 与长连接不要混用

| 模式 | 同时开两个？ |
|------|----------------|
| 只用长连接 | ✅ 推荐 |
| 只用 HTTP Webhook | ✅ 可 |
| 长连接 + HTTP 同时开同一应用 | ❌ 易重复消费 / 难排查 |

若改用 HTTP，请在 Agent Loop **关闭**「WebSocket 长连接」，避免双通道。

---

## 5. 安全设置 / 可用范围 / 发布

### 5.1 安全设置（按需）

| 项 | 建议 |
|----|------|
| IP 白名单 | 长连接模式一般不强制；HTTP 回调若开启白名单，需放行飞书出口 IP（以官方文档为准） |
| 重定向 URL | 本系统不做 OAuth 登录飞书，可空 |

### 5.2 可用范围

路径：**应用发布 → 版本管理与发布 / 可用范围**

| 项 | 建议 |
|----|------|
| 可用成员 | 至少包含会操作任务的人 |
| 是否全员 | 按公司规范；开发阶段建议先小范围 |

机器人要能进群、被 @、收消息，成员需在可用范围内（视租户策略而定）。

### 5.3 发布检查清单

每次改完权限或事件后：

1. [ ] 权限状态 = 已开通  
2. [ ] 事件列表含 `im.message.receive_v1`  
3. [ ] 订阅方式与运行模式一致（长连接 / HTTP）  
4. [ ] **创建版本 → 填写更新说明 → 申请线上发布**（或企业内测试发布）  
5. [ ] 发布状态变为 **已启用**  

未发版时常见现象：后台配置「看着对」，群里机器人完全不回。

---

## 6. 拉群 + Agent Loop 平台配置明细

### 6.1 拉机器人进群

飞书群 → **设置 → 群机器人 / 添加应用** → 选择你的自建应用。

进群后才会有群 `chat_id`（`oc_` 开头）。

### 6.2 配置管理页字段对照表

登录前端 → **配置管理 → 飞书集成**

| 页面字段 | 存库键（参考） | 示例 | 说明 |
|----------|----------------|------|------|
| App ID | `feishu_app_id` | `cli_xxx` | 必填 |
| App Secret | `feishu_app_secret` | `***` | 必填；留空保存表示不改原值 |
| WebSocket 长连接 | `feishu_ws_enabled` | 开启 | 方式 A 必开 |
| 群聊需 @ 机器人 | `feishu_ws_require_mention` | 开启/关闭 | 见 6.3 |
| 飞书群 chat_id | `feishu_chat_group_id` | `oc_xxx` | 与默认项目绑定；拉机器人进群后用「获取群列表」填入 |
| 关联项目 | `feishu_default_project_id` | `1` | 该群消息落到哪个项目 |

亦可在项目「编辑项目」中填写项目级 `chat_id`（匹配优先级见 6.4）。

`.env` 可选初值：

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_WS_ENABLED=true
FEISHU_WS_REQUIRE_MENTION=true
```

> 配置管理页保存后以**数据库**为准；改凭证后点页面 **重新连接**，一般不必重启 `runserver`。

### 6.3 「群聊需 @ 机器人」与权限如何搭配

| 平台开关 | 开放平台权限 | 群里说法 | 效果 |
|----------|--------------|----------|------|
| **开启**（推荐） | `im:message.group_at_msg:readonly` 足够 | `@机器人 新建任务：…` | 未 @ 会被过滤（长连接日志「被过滤」） |
| **关闭** | 还需 `im:message.group_msg`（读全群消息） | `新建任务：…`（可不 @） | 噪音大，易误触 |

未拿到 bot `open_id` 时，@ 过滤可能失效（日志会有警告）；检查 `bot/v3/info` 权限与凭证。

### 6.4 chat_id 匹配顺序

收到消息后的项目解析：

1. **项目表**里 `chat_group_id == 消息 chat_id` 的项目  
2. 否则：消息 `chat_id` == 配置管理中的默认群，且已选 **关联项目**  
3. 否则：回复「未找到匹配项目…」

获取 `chat_id`：

1. 配置页 **获取群列表** → 点击群名填入（需 `im:chat` 类权限）  
2. 或看长连接日志：`收到飞书消息 chat=oc_...`

### 6.5 平台 API 一览（运维）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/feishu/long-connection/status/` | 长连接状态 |
| GET | `/api/feishu/long-connection/logs/` | 最近日志 |
| POST | `/api/feishu/long-connection/restart/` | 重连 |
| GET | `/api/feishu/chats/` | 机器人所在群列表 |

状态含义：

| status | 含义 |
|--------|------|
| `CONNECTED` | 正常收事件 |
| `CONNECTING` | 连接中 |
| `DISABLED` | 未开启长连接 |
| `STOPPED` / 带 error | 凭证、网络、代理或开放平台未保存长连接 |

---

## 7. 联调步骤（建议严格按序）

1. 开放平台：机器人能力 + 必开权限 + 长连接订阅 + `im.message.receive_v1` + **已发布**  
2. 机器人已进目标群  
3. Agent Loop：填 App ID/Secret → 开长连接 → 保存 → 状态 `CONNECTED`  
4. 填 `chat_id` + 关联项目 → 保存  
5. 配置 Anthropic Key  
6. 群内发送（若开启需 @ 则先 @ 机器人）：

```text
新建任务：飞书配置联调
验收标准：能收到 Review 推送
```

7. 预期机器人回复任务号；看板出现任务；拆解后推送含「自动 Review 建议」的摘要  
8. 按 [FEISHU_COMMANDS.md](./FEISHU_COMMANDS.md) 试 `#N 同意动工` / `#N 驳回：…`

前端 **协作消息** 可核对收发记录。

---

## 8. 配置对照总表（打印用）

### 8.1 开放平台

| 分类 | 配置项 | 推荐值 |
|------|--------|--------|
| 凭证 | App ID / App Secret | 已复制到平台 |
| 能力 | 机器人 | 已添加 |
| 权限 | `im:message.group_at_msg:readonly` | 已开通 |
| 权限 | `im:message:send_as_bot` 或 `im:message` | 已开通 |
| 权限 | `im:chat` / `im:chat:readonly` | 已开通（取群列表） |
| 权限 | `im:message.p2p_msg:readonly` | 建议开通 |
| 权限 | `im:message.group_msg` | 仅当关闭「需 @」时 |
| 事件方式 | 长连接 / HTTP | 二选一，推荐长连接 |
| 事件 | `im.message.receive_v1` | 已添加 |
| 回调 | 卡片等 | 不需要 |
| 加密推送 | Encrypt Key | HTTP 勿开加密 |
| HTTP URL | `https://域名/api/feishu/webhook/` | 仅 HTTP 模式 |
| 可用范围 | 成员 | 已包含操作者 |
| 版本 | 线上/企业内 | **已发布** |

### 8.2 Agent Loop

| 配置项 | 推荐值 |
|--------|--------|
| App ID / Secret | 与开放平台一致 |
| WebSocket 长连接 | 开（长连接模式） |
| 群聊需 @ | 与权限策略一致 |
| chat_id | `oc_…` |
| 关联项目 | 已选 |
| 状态 | `CONNECTED` |
| Anthropic Key | 已配 |

---

## 9. 常见问题（配置向）

**Q: 保存长连接提示「应用未建立长连接」？**  
A: 先在 Agent Loop 开启长连接并出现 `CONNECTED`，再回开放平台保存订阅方式。确认只跑一个后端实例。

**Q: 权限已勾但群里无反应？**  
A: 99% 是 **未发版本**。到版本管理确认当前版本已启用。

**Q: 日志「被过滤」？**  
A: 开了「需 @」但消息没 @ 机器人；或 bot open_id 获取失败。

**Q: 能收指令但推送失败？**  
A: 缺 `im:message:send_as_bot` / `im:message`，或机器人不在群、无发言权。看日志 `im/v1/messages` 返回。

**Q: 获取群列表失败/为空？**  
A: 缺 `im:chat` 类权限，或机器人未进任何群，或 Secret 错误。

**Q: HTTP 回调 URL 校验失败？**  
A: 确认返回体是裸 `{"challenge":"..."}`；域名 HTTPS 可达；未开 Encrypt Key。可用 curl 自测 `POST /api/feishu/webhook/`。

**Q: 本机代理导致连不上？**  
A: 飞书域名勿走本地 HTTP 代理。平台已尽量绕过；仍失败则关系统代理或把 `*.feishu.cn` 加入 NO_PROXY。

**Q: 自动 Review 一直跳过？**  
A: 需先有 `#N 驳回：意见` 积累偏好；与机器人开放平台配置无关。

**Q: 配置改了又不生效？**  
A: 开放平台再发一版；Agent Loop 点「重新连接」；确认 `chat_id`、关联项目未空。

---

## 10. 相关文档

| 文档 | 内容 |
|------|------|
| [FEISHU_COMMANDS.md](./FEISHU_COMMANDS.md) | 群内固定指令与错误提示 |
| [USER_MANUAL.md](./USER_MANUAL.md) | 平台使用概览 |
| [QUICK_TEST.md](./QUICK_TEST.md) | 端到端快速测试 |

配置以飞书开放平台**当前后台文案**为准；若权限中文名微调，请用本文 **Scope 关键词** 搜索开通。
