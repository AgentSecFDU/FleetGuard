#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# 员工容器入口 — 启动 Sidecar + 保持容器运行
# ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║   FleetGuard Employee Machine                       ║"
echo "║   Hostname: ${FG_HOSTNAME:-unknown}                  ║"
echo "║   Device:   ${FG_DEVICE_ID:-unknown}                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 导出环境变量给 Sidecar
export FG_CONTROL_CENTER_URL="${FG_CONTROL_CENTER_URL:-http://api:8000}"
export FG_ENROLLMENT_TOKEN="${FG_ENROLLMENT_TOKEN}"
export FG_DEVICE_ID="${FG_DEVICE_ID}"
export FG_HOSTNAME="${FG_HOSTNAME:-$(hostname)}"
export FG_USERNAME="${FG_USERNAME:-employee}"
export FG_OS="${FG_OS:-Linux}"

# 如果还没注册过，生成 device_id
if [ -z "$FG_DEVICE_ID" ]; then
  export FG_DEVICE_ID="fg-dev-$(hostname)-$(date +%s | tail -c5)"
fi

# ── 重建 Plugin 符号链接（volume 挂载会覆盖 /root/.openclaw）──
mkdir -p /root/.openclaw/extensions
ln -sf /opt/fleetguard-plugin /root/.openclaw/extensions/fleetguard

echo -e "${YELLOW}  Control Center: ${FG_CONTROL_CENTER_URL}${NC}"
echo -e "${YELLOW}  Device ID:      ${FG_DEVICE_ID}${NC}"
echo ""

# ── 等待管控端就绪 ─────────────────────────────────────────────
echo -e "${YELLOW}→ 等待管控端就绪...${NC}"
for i in $(seq 1 60); do
  if curl -s "${FG_CONTROL_CENTER_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ 管控端已就绪${NC}"
    break
  fi
  sleep 2
done

# ── 自动获取注册令牌 ─────────────────────────────────────────────
echo -e "${YELLOW}→ 获取注册令牌...${NC}"

ADMIN_RESP=$(curl -s -X POST "${FG_CONTROL_CENTER_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')
ADMIN_TOKEN=$(echo "$ADMIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [ -n "$ADMIN_TOKEN" ]; then
  ENROLL_RESP=$(curl -s -X POST "${FG_CONTROL_CENTER_URL}/api/v1/auth/enrollment-token" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}")
  NEW_TOKEN=$(echo "$ENROLL_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")
  if [ -n "$NEW_TOKEN" ]; then
    export FG_ENROLLMENT_TOKEN="$NEW_TOKEN"
    echo -e "${GREEN}  ✅ 获取到注册令牌: ${NEW_TOKEN:0:20}...${NC}"
  fi
fi
echo ""

# ── 启动 Sidecar（后台）────────────────────────────────────────────
echo -e "${GREEN}→ 启动 FleetGuard Sidecar...${NC}"
cd /opt/fleetguard/sidecar
export PYTHONPATH="/opt/fleetguard/sidecar/src:$PYTHONPATH"
uv run python -m fleetguard_sidecar.main --api-port 18900 &
SIDECAR_PID=$!

# 等待 Sidecar 启动
sleep 3

# 检查 Sidecar 是否正常
if curl -s http://127.0.0.1:18900/local/status > /dev/null 2>&1; then
  echo -e "${GREEN}  ✅ Sidecar 已启动 (localhost:18900)${NC}"
else
  echo -e "${YELLOW}  ⚠️  Sidecar 可能还在注册中...${NC}"
fi
echo ""

# ── OpenClaw 配置检查 ──────────────────────────────────────────────
OC_CONFIGURED=false

# 检查是否已配置（.env 文件中有实际的 API Key）
if [ -f "${HOME}/.openclaw/.env" ]; then
  if grep -qE '^[A-Z_]+=sk-|^[A-Z_]+=gsk_|^[A-Z_]+=xai-' "${HOME}/.openclaw/.env" 2>/dev/null; then
    OC_CONFIGURED=true
    echo -e "${GREEN}  ✅ OpenClaw 已配置${NC}"
  else
    echo -e "${YELLOW}  ⚠️  OpenClaw 未配置，请运行 openclaw onboard${NC}"
  fi
else
  echo -e "${YELLOW}  ⚠️  OpenClaw 未配置，请运行 openclaw onboard${NC}"
fi
echo ""

# ── 构建状态信息 ────────────────────────────────────────────────────
if [ "$OC_CONFIGURED" = true ]; then
  OC_LINE1="OpenClaw:   ✅ 已配置"
  OC_LINE2="  启动: openclaw gateway start"
else
  OC_LINE1="OpenClaw:   ⚠️  未配置"
  OC_LINE2="  配置: openclaw onboard"
fi

echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ 员工环境就绪                                     ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  ${OC_LINE1}                        ║${NC}"
echo -e "${GREEN}║  ${OC_LINE2}                        ║${NC}"
echo -e "${GREEN}║  Sidecar:    http://localhost:18900                  ║${NC}"
echo -e "${GREEN}║  Plugin:     ~/.openclaw/extensions/fleetguard       ║${NC}"
echo -e "${GREEN}║  (已接入 OpenClaw，自动拦截工具调用)                   ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  进入容器:                                           ║${NC}"
echo -e "${GREEN}║    docker exec -it <容器名> bash                     ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ── 保持容器运行 ───────────────────────────────────────────────────
echo "容器运行中。docker exec -it <容器名> bash 进入。"
echo ""

# Keep container alive even if sidecar exits (for debugging)
# Restart sidecar if it dies
while true; do
  if ! kill -0 $SIDECAR_PID 2>/dev/null; then
    echo "⚠️  Sidecar stopped, restarting in 5s..."
    sleep 5
    cd /opt/fleetguard/sidecar
    export PYTHONPATH="/opt/fleetguard/sidecar/src:$PYTHONPATH"
    uv run python -m fleetguard_sidecar.main --api-port 18900 &
    SIDECAR_PID=$!
  fi
  sleep 10
done
