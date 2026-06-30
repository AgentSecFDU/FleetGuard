# AgentFleetControl Employee Machine

预装完整的员工工作环境：OpenClaw + AgentFleetControl Sidecar + AgentFleetControl Plugin。

## 预装组件

| 组件 | 位置 | 说明 |
|------|------|------|
| Node.js 24 | 系统安装 | OpenClaw 运行时 |
| Python 3.12 | 系统安装 | Sidecar 运行时 |
| OpenClaw Gateway | `npm install -g openclaw` | AI Agent 网关 |
| AgentFleetControl Sidecar | `/opt/afc/sidecar/` | 自动启动，监听 `:18900` |
| AgentFleetControl Plugin | `~/.openclaw/extensions/afc` | 已接入 OpenClaw |

## 启动后

容器启动后自动完成：等待管控端就绪 → 获取注册令牌 → 注册设备 → 启动 Sidecar → 心跳上报。

进入容器：
```bash
docker exec -it afc-employee-alice bash
```

## 配置 OpenClaw

OpenClaw 已全局安装，Plugin 已就位。在启动 OpenClaw Gateway 之前，需要配置 API Key。

### 方式一：openclaw onboard（推荐）

进入容器后运行 OpenClaw 自带的配置向导：

```bash
openclaw onboard
```

交互式引导，支持 Anthropic、OpenAI、OpenRouter、Google Gemini 等多个提供商。

### 方式二：手动写配置文件

容器内已预置了配置模板，直接编辑填入 Key 即可：

```bash
# API Key
vim ~/.openclaw/.env
# 取消注释你使用的 Provider，填入 Key

# 模型设置
vim ~/.openclaw/openclaw.json
# 修改 agents.defaults.model.primary
```

## 启动 OpenClaw

配置完成后启动：

```bash
openclaw gateway start
```

此后每一次工具调用都会被 AgentFleetControl Plugin 拦截 → Sidecar 评估 → Control Center 审计。

## 验证

```bash
# Sidecar 状态
curl http://127.0.0.1:18900/local/status

# 模拟一次工具调用（测试链路）
curl -X POST http://127.0.0.1:18900/local/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "before_tool_call",
    "tool_name": "exec",
    "tool_category": "shell",
    "params_summary": "ls -la",
    "session_id": "test_001",
    "risk_score": 0
  }'
```
