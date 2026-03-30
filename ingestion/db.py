"""
asyncpg connection pool for PostgreSQL.
"""
from __future__ import annotations

import os
from typing import Optional

import asyncpg


_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", 5432)),
            database=os.environ.get("POSTGRES_DB", "aura"),
            user=os.environ.get("POSTGRES_USER", "aura"),
            password=os.environ.get("POSTGRES_PASSWORD", "aura_secret"),
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def lookup_room_for_ap(ap_name: str) -> Optional[int]:
    """Return room_id for a given AP name, or None if not found."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT room_id FROM access_points WHERE ap_name = $1", ap_name
    )
    return row["room_id"] if row else None


async def lookup_user_id(student_id: str) -> Optional[int]:
    """Return users.id for a given student_id (RADIUS User-Name)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id FROM users WHERE student_id = $1", student_id
    )
    return row["id"] if row else None
