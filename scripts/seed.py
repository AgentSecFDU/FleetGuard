#!/usr/bin/env python3
"""Seed script: creates default admin user, enrollment token, and default policies."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select
from fleetguard.database import async_session_factory, engine
from fleetguard.models import Base, AdminUser, EnrollmentToken, Policy
from fleetguard.utils.crypto import hash_password, hash_token


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Admin user
        result = await db.execute(select(AdminUser).where(AdminUser.username == "admin"))
        if not result.scalar_one_or_none():
            admin = AdminUser(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            print("✅ Created admin user (admin / admin123)")

        # Enrollment token
        raw_token = "fget_demo-enrollment-token-for-testing-00000000"
        result = await db.execute(select(EnrollmentToken).where(EnrollmentToken.token_prefix == raw_token[:12]))
        if not result.scalar_one_or_none():
            tok = EnrollmentToken(
                token_hash=hash_token(raw_token),
                token_prefix=raw_token[:12],
                used=False,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                created_by="seed",
            )
            db.add(tok)
            print(f"✅ Created enrollment token: {raw_token}")

        # Default policy
        result = await db.execute(
            select(Policy).where(Policy.policy_id == "default", Policy.status == "published")
        )
        if not result.scalar_one_or_none():
            policy_path = Path(__file__).parent.parent / "policies" / "default.yaml"
            with open(policy_path) as f:
                yaml_content = f.read()
            policy = Policy(
                policy_id="default",
                name="Default Policy",
                version=1,
                yaml_content=yaml_content,
                status="published",
                created_by="seed",
                published_at=datetime.now(timezone.utc),
            )
            db.add(policy)
            print("✅ Created default policy (published)")

        # Lockdown policy
        result = await db.execute(
            select(Policy).where(Policy.policy_id == "lockdown", Policy.status == "published")
        )
        if not result.scalar_one_or_none():
            policy_path = Path(__file__).parent.parent / "policies" / "lockdown.yaml"
            with open(policy_path) as f:
                yaml_content = f.read()
            policy = Policy(
                policy_id="lockdown",
                name="Lockdown Policy",
                version=1,
                yaml_content=yaml_content,
                status="published",
                created_by="seed",
                published_at=datetime.now(timezone.utc),
            )
            db.add(policy)
            print("✅ Created lockdown policy (published)")

        await db.commit()
        print("🎉 Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
