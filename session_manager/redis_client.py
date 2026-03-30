"""
Redis Session Manager — live session state for every active device.

Key schema:
    aura:session:{username}  →  HASH {
        username, room_id, connect_time, ap_name,
        bytes_in, bytes_out
    }

    aura:active_sessions  →  SET of active usernames
"""
from __future__ import annotations

import os
from typing import Any, Optional

import redis.asyncio as aioredis

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_SESSION_PREFIX = "aura:session:"
_ACTIVE_SET = "aura:active_sessions"
# Sessions expire after 8 hours if no Stop event arrives (safety net)
_SESSION_TTL_SECONDS = 8 * 60 * 60


def _session_key(username: str) -> str:
    return f"{_SESSION_PREFIX}{username}"


def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(_REDIS_URL, decode_responses=True)


async def session_open(
    username: str,
    room_id: Optional[int],
    connect_time: Optional[str],
    ap_name: str,
) -> None:
    """Create a new live session hash in Redis."""
    async with _get_redis() as r:
        key = _session_key(username)
        await r.hset(key, mapping={
            "username": username,
            "room_id": str(room_id) if room_id is not None else "",
            "connect_time": connect_time or "",
            "ap_name": ap_name,
            "bytes_in": "0",
            "bytes_out": "0",
        })
        await r.expire(key, _SESSION_TTL_SECONDS)
        await r.sadd(_ACTIVE_SET, username)


async def session_update(
    username: str,
    bytes_in: int,
    bytes_out: int,
) -> None:
    """
    Overwrite byte counters with the latest values from Interim-Update or Stop.
    WLC sends cumulative totals, not deltas — so we set, not increment.
    """
    async with _get_redis() as r:
        key = _session_key(username)
        if not await r.exists(key):
            return
        await r.hset(key, mapping={
            "bytes_in": str(bytes_in),
            "bytes_out": str(bytes_out),
        })
        await r.expire(key, _SESSION_TTL_SECONDS)


async def session_close(username: str) -> Optional[dict[str, Any]]:
    """
    Retrieve and delete the live session. Returns the session dict or None.
    """
    async with _get_redis() as r:
        key = _session_key(username)
        data = await r.hgetall(key)
        if not data:
            return None
        pipeline = r.pipeline()
        pipeline.delete(key)
        pipeline.srem(_ACTIVE_SET, username)
        await pipeline.execute()
        return _deserialize_session(data)


async def get_session(username: str) -> Optional[dict[str, Any]]:
    """Return a single live session dict without closing it."""
    async with _get_redis() as r:
        data = await r.hgetall(_session_key(username))
        return _deserialize_session(data) if data else None


async def get_all_active_sessions() -> list[dict[str, Any]]:
    """Return all currently active sessions from Redis."""
    async with _get_redis() as r:
        usernames = await r.smembers(_ACTIVE_SET)
        sessions = []
        for username in usernames:
            data = await r.hgetall(_session_key(username))
            if data:
                sessions.append(_deserialize_session(data))
        return sessions


def _deserialize_session(data: dict) -> dict[str, Any]:
    room_id_raw = data.get("room_id", "")
    return {
        "username": data.get("username", ""),
        "room_id": int(room_id_raw) if room_id_raw.lstrip("-").isdigit() else None,
        "connect_time": data.get("connect_time", ""),
        "ap_name": data.get("ap_name", ""),
        "bytes_in": int(data.get("bytes_in", 0)),
        "bytes_out": int(data.get("bytes_out", 0)),
        "bytes_downloaded_mb": round(int(data.get("bytes_out", 0)) / (1024 * 1024), 3),
        "bytes_uploaded_mb": round(int(data.get("bytes_in", 0)) / (1024 * 1024), 3),
    }
