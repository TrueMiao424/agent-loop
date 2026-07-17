# 代码规范

本项目采用分层架构与高并发友好设计，并结合 Django / Vue 最佳实践。

## 1. 目录分层

| 目录 | 职责 | 禁止 |
|------|------|------|
| `controller/` | 参数校验、调用 Service、返回统一响应 | 写业务逻辑、直接操作 ORM |
| `service/` | 业务流程、事务、状态机 | 直接返回 HTTP Response |
| `dao/` | CRUD、查询封装 | 复杂业务判断 |
| `entity/` | Django Model | 跨层引用 View |
| `dto/` | Serializer / 入参出参 | 业务逻辑 |
| `client/` | 外部 HTTP / SDK 调用 | 数据库操作 |
| `common/service/` | Redis 缓存、会话、限流 | 业务状态机 |
| `common/middleware/` | TraceID、AccessLog、RateLimit | 业务逻辑 |

## 2. 命名规范

- Python：模块/函数 `snake_case`，类 `PascalCase`
- Vue：组件 `PascalCase.vue`，组合式函数 `useXxx`
- API 路径：小写 + 连字符，如 `/api/tasks/{id}/review1/`
- 数据库表：`snake_case`，如 `agent_sessions`

## 3. 日志规范

- **Service / DAO / Client** 方法使用 `@log_method`（DEBUG 入参/出参）
- **外部调用** 使用 `log_external_call` 记录 request/response/耗时
- **API 入站** 由 `AccessLogMiddleware` 记录 method/path/status/duration
- 禁止打印 password、api_key、token 明文
- 全链路 TraceID：`X-Trace-Id` 请求头

## 4. Session 规范

- JWT 登录态，Redis 缓存用户 profile（`SessionCacheService`）
- Agent Session 入库 + Redis 元数据
- 任务中断通过 Redis 取消信号 + checkpoint 协作式取消

## 5. 异常与返回

- 业务异常抛 `BizException`，由全局 handler 转为 `{ code, msg, data, success }`
- Controller 禁止裸抛未处理异常
- 限流返回 `429` / `RATE_LIMIT`

## 6. 数据库与高并发

- 查询必须带索引字段
- 连接池参数在 `.env` 配置：`DB_POOL_SIZE`、`DB_MAX_OVERFLOW`
- 写接口支持幂等（`X-Idempotency-Key`）
- API 限流：`API_RATE_LIMIT_PER_MINUTE`（默认 120/min/用户）

## 7. 前端规范

- API 调用统一走 `src/api/`
- 全局状态用 Pinia
- 登录 / 注册页独立路由；401 自动 refresh，失败跳转登录
- 中断/续做必须有用户确认与 Toast 提示
- 失败任务展示 `failReason`
- 轮询间隔约 5s，避免并发风暴

## 8. Git 提交

- feat / fix / docs / refactor 前缀
- 单次提交聚焦单一变更

## 9. Code Review Checklist

- [ ] Controller 无业务逻辑
- [ ] Service / DAO 方法有 @log_method
- [ ] 外调有 request/response 日志
- [ ] API 有 AccessLog
- [ ] 新接口有权限控制
- [ ] 写接口考虑幂等
- [ ] 前端中断/失败有续做入口
- [ ] Agent 任务使用线程池 + 调度锁
