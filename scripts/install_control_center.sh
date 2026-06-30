#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# Agentfleetcontrol Control Center — 一键安装脚本
# 运行在公司服务器上
# ────────────────────────────────────────────────────────────────────
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Agentfleetcontrol Control Center — 一键安装               ║"
echo "║   集中管控端，装在公司服务器上                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 0: Check prerequisites ────────────────────────────────────
echo -e "${YELLOW}[0/4] 检查环境...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ 未找到 Python3，请先安装 Python 3.12+${NC}"
    echo "   macOS: brew install python@3.12"
    echo "   Ubuntu: sudo apt install python3.12"
    exit 1
fi

if ! command -v uv &>/dev/null; then
    echo -e "${YELLOW}  安装 uv 包管理器...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}  ✅ Python ${PYTHON_VERSION} + uv 就绪${NC}"

# ── Step 1: Configure ──────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[1/4] 配置 Control Center...${NC}"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.local" "$PROJECT_DIR/.env"

    read -p "  数据库地址 (默认 SQLite 本地): " DB_URL
    DB_URL=${DB_URL:-sqlite+aiosqlite:///afc.db}

    read -p "  JWT 密钥 (回车随机生成): " JWT_KEY
    JWT_KEY=${JWT_KEY:-$(python3 -c "import secrets; print(secrets.token_hex(32))")}

    read -p "  API 端口 (默认 8000): " API_PORT
    API_PORT=${API_PORT:-8000}

    # Write .env
    cat > "$PROJECT_DIR/.env" << EOF
DATABASE_URL=${DB_URL}
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=${JWT_KEY}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
DEVICE_OFFLINE_THRESHOLD_SECONDS=300
APPROVAL_TIMEOUT_SECONDS=120
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
APP_NAME=Agentfleetcontrol Control Center
DEBUG=false
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}  ✅ 配置已保存到 .env${NC}"
else
    echo -e "${GREEN}  ✅ 已有配置，跳过${NC}"
fi

# ── Step 2: Install dependencies ───────────────────────────────────
echo ""
echo -e "${YELLOW}[2/4] 安装依赖...${NC}"
cd "$PROJECT_DIR"
uv sync
echo -e "${GREEN}  ✅ 依赖安装完成${NC}"

# ── Step 3: Initialize database ────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/4] 初始化数据库...${NC}"
uv run python -c "
import asyncio
from afc.database import engine, async_session_factory
from afc.models import Base
from afc.models.admin_user import AdminUser
from afc.models.policy import Policy
from afc.models.enrollment_token import EnrollmentToken
from afc.utils.crypto import hash_password, hash_token
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import select

async def setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as db:
        r = await db.execute(select(AdminUser).where(AdminUser.username == 'admin'))
        if not r.scalar_one_or_none():
            db.add(AdminUser(username='admin', password_hash=hash_password('admin123'), role='admin'))
        raw = 'afcet_demo-token-for-local-dev-0000000000'
        r = await db.execute(select(EnrollmentToken).where(EnrollmentToken.token_prefix == raw[:12]))
        if not r.scalar_one_or_none():
            db.add(EnrollmentToken(token_hash=hash_token(raw), token_prefix=raw[:12],
                    expires_at=datetime.now(timezone.utc)+timedelta(days=365), created_by='install'))
        r = await db.execute(select(Policy).where(Policy.policy_id == 'default', Policy.status == 'published'))
        if not r.scalar_one_or_none():
            p = Path('policies/default.yaml')
            if p.exists():
                db.add(Policy(policy_id='default', name='Default Policy', version=1,
                       yaml_content=p.read_text(), status='published', created_by='install',
                       published_at=datetime.now(timezone.utc)))
        await db.commit()
    await engine.dispose()
asyncio.run(setup())
"
echo -e "${GREEN}  ✅ 数据库初始化完成${NC}"

# ── Step 4: Start ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Agentfleetcontrol Control Center 安装完成！              ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  启动命令:                                            ║${NC}"
echo -e "${GREEN}║    ./scripts/start_dev.sh                             ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  访问:                                                ║${NC}"
echo -e "${GREEN}║    API:  http://<服务器IP>:8000/docs                  ║${NC}"
echo -e "${GREEN}║    前端: cd frontend && npm run dev -- --host 0.0.0.0 ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  管理员: admin / admin123                             ║${NC}"
echo -e "${GREEN}║  设备注册口令: afcet_demo-token-for-local-dev-...       ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  创建更多注册口令:                                     ║${NC}"
echo -e "${GREEN}║    curl -X POST http://localhost:8000/api/v1/auth/    ║${NC}"
echo -e "${GREEN}║      enrollment-token -H \"Authorization: Bearer      ║${NC}"
echo -e "${GREEN}║      \$(curl -s -X POST http://localhost:8000/api/    ║${NC}"
echo -e "${GREEN}║      v1/auth/login -H 'Content-Type: application/    ║${NC}"
echo -e "${GREEN}║      json' -d '{\"username\":\"admin\",\"password\":     ║${NC}"
echo -e "${GREEN}║      \"admin123\"}' | python3 -c 'import sys,json;     ║${NC}"
echo -e "${GREEN}║      print(json.load(sys.stdin)[\"access_token\"])')   ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
