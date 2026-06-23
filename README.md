# FleetGuard

**Centralized Runtime Governance for Local AI Agent Fleets**

FleetGuard 是一个面向本地 AI Agent 集群的集中式运行时治理系统。它将多台设备上分散运行的 AI Agent（基于 OpenClaw）纳入统一管理，提供：

- 🔍 **实时监控** — 集中观察每台设备的 agent 行为、工具调用记录
- 🛡️ **事前拦截** — 在危险工具调用执行前进行阻断
- 📋 **策略管理** — 统一下发安全策略，本地缓存，断网也能生效
- ⚠️ **风险检测** — 间接提示词注入、危险命令、敏感数据外发、持久化污染
- ✅ **审批流程** — 高风险操作需要管理员 approve/deny
- 🔒 **一键隔离** — 设备/session 进入 lockdown 模式

---

## 快速开始

### 前置条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 包管理器
- PostgreSQL 16 + Redis 7 (或 Docker)

### 1. 启动基础设施

```bash
docker compose up -d postgres redis
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 初始化数据库

```bash
uv run alembic upgrade head
uv run python scripts/seed.py
```

### 4. 启动 API 服务

```bash
uv run uvicorn fleetguard.main:app --reload
```

访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 5. 生成 Demo 数据

```bash
uv run python scripts/demo_data.py
```

### 6. 运行测试

```bash
uv run pytest tests/ -v
```

---

## 默认账号

| 用途 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `admin123` |

### Demo 注册令牌

```
fget_demo-enrollment-token-for-testing-00000000
```

---

## API 概览

所有 API 在 `/api/v1/` 下：

| 模块 | 端点 | 说明 |
|------|------|------|
| Auth | `POST /auth/login` | 管理员登录 |
| Auth | `POST /auth/enrollment-token` | 生成设备注册令牌 |
| Devices | `POST /devices/enroll` | 设备注册 |
| Devices | `POST /devices/heartbeat` | 设备心跳 |
| Devices | `POST /devices/{id}/quarantine` | 隔离设备 |
| Events | `POST /events/batch` | 批量上传事件 |
| Events | `GET /events/` | 查询事件 (支持 cursor 分页) |
| Policies | `GET /policies/` | 策略列表 |
| Policies | `POST /policies/{id}/publish` | 发布策略 |
| Approvals | `POST /approvals/` | 创建审批 |
| Approvals | `POST /approvals/{id}/approve` | 批准 |
| Dashboard | `GET /dashboard/summary` | 仪表盘摘要 |
| Dashboard | `GET /dashboard/risk-trends` | 风险趋势 |
| WebSocket | `/ws/dashboard` | 实时事件推送 |

---

## 项目结构

```
fleetguard/
├── src/fleetguard/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理 (pydantic-settings)
│   ├── database.py          # 异步数据库引擎
│   ├── deps.py              # 认证依赖注入
│   ├── models/              # SQLAlchemy ORM 模型 (8 张表)
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── api/v1/              # REST API 路由
│   ├── services/            # 业务逻辑层
│   ├── engine/              # 风险引擎 + 策略引擎
│   │   └── rules/           # 5 条风险检测规则
│   ├── websocket/           # WebSocket 连接管理
│   ├── middleware/           # 认证、审计、CORS
│   └── utils/               # ID生成、JWT、YAML解析
├── policies/                # 策略 YAML 文件
├── scripts/                 # 种子数据、Demo 数据
├── alembic/                 # 数据库迁移
└── tests/                   # 测试
```

---

## 风险引擎

内置 5 条检测规则，每条独立评分 (0-100)，聚合后分级：

| 规则 | 检测内容 | 示例 |
|------|---------|------|
| DangerousShell | 危险 shell 命令 | `curl \| sh`, `rm -rf /`, `bash -c` |
| SensitivePath | 敏感文件访问 | `~/.ssh/id_rsa`, `.env`, `Cookies` |
| Exfiltration | 数据外发 | 外部邮箱、pastebin、webhook |
| PromptInjection | 间接提示词注入 | "ignore previous instructions" 等 |
| Persistence | 持久化污染 | memory/plugin/config 写入 |

支持未来接入 ML 模型 — 实现 `RiskRule` 接口即可。

---

## 演示场景

1. **多设备接入** — 3 台设备同时注册，Dashboard 展示在线状态
2. **普通工具调用审计** — 低风险命令记录为 allow
3. **危险命令阻断** — `curl ... | sh` 在 before_tool_call 阶段阻断
4. **敏感文件读取审批** — 读取 SSH key 触发审批，管理员 approve/deny
5. **间接提示词注入** — 恶意网页诱导读取敏感文件并外发，被检测阻断
6. **一键隔离** — 管理员点击 Quarantine，设备进入 lockdown

---

## 当前限制 (MVP)

- 不做完整 EDR
- 不做深度系统调用监控
- 不做复杂 RBAC (仅 admin/user)
- 不做生产级高可用
- 不做复杂 LLM 风险判定模型
- 不默认上传完整聊天记录

## 后续计划

- 多租户和组织架构
- 更细粒度 RBAC
- LLM-based risk classifier
- 数据流追踪 (taint tracking)
- SIEM / Slack / 飞书集成
- Agent 行为图谱
