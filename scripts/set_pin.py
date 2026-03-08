"""
Set a user's PIN.

Usage:
    python3 -m scripts.set_pin <username> <new_pin>

Example:
    python3 -m scripts.set_pin Julie 9876
"""
from __future__ import annotations

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from backend.app.database import engine, async_session, Base
from backend.app.models import User
from backend.app.services.auth_service import hash_pin


async def set_pin(name: str, new_pin: str) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        result = await db.execute(select(User).where(User.name == name))
        user = result.scalar_one_or_none()
        if not user:
            print(f"❌  User '{name}' not found.")
            return
        user.pin_hash = hash_pin(new_pin)
        await db.commit()
        print(f"✅  PIN updated for {user.name}.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 -m scripts.set_pin <username> <new_pin>")
        sys.exit(1)
    asyncio.run(set_pin(sys.argv[1], sys.argv[2]))
