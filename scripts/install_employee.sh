#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# Agentfleetcontrol Employee Sidecar — 一键安装脚本
# 运行在每台员工电脑上
# ────────────────────────────────────────────────────────────────────
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Agentfleetcontrol Employee Sidecar — 一键安装             ║"
echo "║   员工端，装在每台员工电脑上                           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 0: Check prerequisites ────────────────────────────────────
echo -e "${YELLOW}[0/3] 检查环境...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ 未找到 Python3，请先安装 Python 3.12+${NC}"
    echo "   macOS: brew install python@3.12"
    echo "   Ubuntu: sudo apt install python3.12"
    exit 1
fi

if ! command -v uv &>/dev/null; then
    echo -e "${YELLOW}  安装 uv 包管理器...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo -e "${GREEN}  ✅ Python + uv 就绪${NC}"

# ── Step 1: Configure ──────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[1/3] 配置 Sidecar...${NC}"
echo -e "  请向管理员索取以下信息:"
echo ""

read -p "  管控端地址 (例: http://192.168.1.100:8000): " CC_URL
if [ -z "$CC_URL" ]; then
    echo -e "${RED}❌ 管控端地址不能为空${NC}"
    exit 1
fi

read -p "  设备注册口令 (管理员提供): " ENROLL_TOKEN
if [ -z "$ENROLL_TOKEN" ]; then
    echo -e "${RED}❌ 注册口令不能为空${NC}"
    exit 1
fi

# Auto-detect hostname
HOSTNAME=$(hostname)
read -p "  设备名称 (默认: $HOSTNAME): " DEVICE_HOST
DEVICE_HOST=${DEVICE_HOST:-$HOSTNAME}

USERNAME=$(whoami)
read -p "  用户名 (默认: $USERNAME): " DEVICE_USER
DEVICE_USER=${DEVICE_USER:-$USERNAME}

# Write config
CONFIG_DIR="$HOME/.afc"
mkdir -p "$CONFIG_DIR"

python3 -c "
import json, platform, uuid
config = {
    'device_id': f'afc-dev-{uuid.uuid4().hex[:8]}',
    'hostname': '$DEVICE_HOST',
    'username': '$DEVICE_USER',
    'os_name': platform.system(),
    'os_version': platform.release(),
    'control_center_url': '$CC_URL',
    'enrollment_token': '$ENROLL_TOKEN',
    'sidecar_version': '0.1.0',
}
with open('$CONFIG_DIR/config.json', 'w') as f:
    json.dump(config, f, indent=2)
print(f'  ✅ 配置已保存到 $CONFIG_DIR/config.json')
"

echo ""
echo -e "${GREEN}  ✅ 配置完成${NC}"

# ── Step 2: Install dependencies ───────────────────────────────────
echo ""
echo -e "${YELLOW}[2/3] 安装依赖...${NC}"
cd "$PROJECT_DIR/sidecar"
uv sync
echo -e "${GREEN}  ✅ 依赖安装完成${NC}"

# ── Step 3: Start ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Agentfleetcontrol Sidecar 安装完成！                     ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  启动命令:                                            ║${NC}"
echo -e "${GREEN}║    cd sidecar                                        ║${NC}"
echo -e "${GREEN}║    uv run python -m afc_sidecar.main           ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  本地 API: http://127.0.0.1:18900                    ║${NC}"
echo -e "${GREEN}║  管控端:   $CC_URL                       ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  设为开机自启动 (macOS):                              ║${NC}"
echo -e "${GREEN}║    cp scripts/afc-sidecar.plist                ║${NC}"
echo -e "${GREEN}║      ~/Library/LaunchAgents/                          ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"

# Ask if start now
echo ""
read -p "  是否立即启动 Sidecar？[Y/n] " START_NOW
if [ "$START_NOW" != "n" ] && [ "$START_NOW" != "N" ]; then
    echo -e "${YELLOW}  启动 Sidecar... (Ctrl+C 停止)${NC}"
    echo ""
    cd "$PROJECT_DIR/sidecar"
    exec uv run python -m afc_sidecar.main
fi
