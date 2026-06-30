#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# Agentfleetcontrol — Zero-dependency local development start
# ────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")/.."

# Use SQLite — no Docker/PostgreSQL needed
export DATABASE_URL="sqlite+aiosqlite:///afc.db"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="afc-local-dev-secret-key"
export CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
export DEBUG="true"
export DEVICE_OFFLINE_THRESHOLD_SECONDS="300"

echo "╔════════════════════════════════════════════╗"
echo "║   Agentfleetcontrol — Local Dev Mode (SQLite)    ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# 1. Create tables and seed data
echo "[1/2] Setting up database (SQLite)..."
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
        # Admin user
        r = await db.execute(select(AdminUser).where(AdminUser.username == 'admin'))
        if not r.scalar_one_or_none():
            db.add(AdminUser(username='admin', password_hash=hash_password('admin123'), role='admin'))
            print('  ✅ Admin user created (admin / admin123)')

        # Enrollment token
        raw = 'afcet_demo-token-for-local-dev-0000000000'
        r = await db.execute(select(EnrollmentToken).where(EnrollmentToken.token_prefix == raw[:12]))
        if not r.scalar_one_or_none():
            db.add(EnrollmentToken(token_hash=hash_token(raw), token_prefix=raw[:12],
                    expires_at=datetime.now(timezone.utc)+timedelta(days=365), created_by='dev'))
            print(f'  ✅ Enrollment token: {raw}')

        # Default policy
        r = await db.execute(select(Policy).where(Policy.policy_id == 'default', Policy.status == 'published'))
        if not r.scalar_one_or_none():
            p = Path('policies/default.yaml')
            if p.exists():
                db.add(Policy(policy_id='default', name='Default Policy', version=1,
                       yaml_content=p.read_text(), status='published', created_by='dev',
                       published_at=datetime.now(timezone.utc)))
                print('  ✅ Default policy loaded')

        await db.commit()
    await engine.dispose()

asyncio.run(setup())
"
echo "  ✅ Database ready"
echo ""

# 2. Start API server
echo "[2/2] Starting Agentfleetcontrol API on http://localhost:8000 ..."
echo ""
echo "  ╔════════════════════════════════════════════╗"
echo "  ║  API Docs:  http://localhost:8000/docs     ║"
echo "  ║  Admin:     admin / admin123               ║"
echo "  ╚════════════════════════════════════════════╝"
echo ""
uv run uvicorn afc.main:app --reload --host 0.0.0.0 --port 8000
