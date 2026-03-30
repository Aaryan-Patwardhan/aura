"""
Session Finalizer Worker.

Subscribes to Redis channel `aura:events:stop`.
For each stop event:
  1. Extracts session data
  2. Resolves the matching schedule (room + time overlap)
  3. Calculates minutes_present
  4. Applies 75% attendance threshold → PRESENT / PARTIAL / ABSENT
  5. Runs Focus Score AI model
  6. Writes finalized attendance_sessions record to PostgreSQL

Run:
    python -m finalizer.session_finalizer
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, time
from typing import Optional

import asyncpg
import redis.asyncio as aioredis

# Import AI scorer — model loaded lazily on first call
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.focus_score import score_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("aura.finalizer")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CHANNEL = "aura:events:stop"

POSTGRES_DSN = (
    f"postgresql://{os.environ.get('POSTGRES_USER', 'aura')}"
    f":{os.environ.get('POSTGRES_PASSWORD', 'aura_secret')}"
    f"@{os.environ.get('POSTGRES_HOST', 'localhost')}"
    f":{os.environ.get('POSTGRES_PORT', 5432)}"
    f"/{os.environ.get('POSTGRES_DB', 'aura')}"
)


async def get_db_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn=POSTGRES_DSN, min_size=1, max_size=5)


async def resolve_schedule(
    pool: asyncpg.Pool,
    room_id: Optional[int],
    connect_dt: Optional[datetime],
) -> Optional[asyncpg.Record]:
    """
    Find the schedule that best matches this session:
    - Same room
    - Day of week matches
    - Session start overlaps the scheduled lecture window (±15 min tolerance)
    """
    if not room_id or not connect_dt:
        return None

    day_of_week = connect_dt.weekday()  # 0=Monday
    connect_time = connect_dt.time()
    tolerance_minutes = 15

    rows = await pool.fetch(
        """
        SELECT id, course_code, course_name, start_time, end_time, min_attendance_pct
        FROM schedules
        WHERE room_id = $1
          AND day_of_week = $2
          AND start_time <= ($3::time + interval '15 minutes')
          AND end_time   >= ($3::time - interval '15 minutes')
        ORDER BY ABS(EXTRACT(EPOCH FROM (start_time - $3::time)))
        LIMIT 1
        """,
        room_id,
        day_of_week,
        connect_time,
    )
    return rows[0] if rows else None


def calculate_minutes_present(
    connect_dt: Optional[datetime],
    disconnect_dt: Optional[datetime],
    acct_session_time: Optional[int],
) -> int:
    """Calculate session duration in minutes."""
    if acct_session_time:
        return max(0, acct_session_time // 60)
    if connect_dt and disconnect_dt:
        delta = disconnect_dt - connect_dt
        return max(0, int(delta.total_seconds() // 60))
    return 0


def determine_status(
    minutes_present: int,
    schedule: Optional[asyncpg.Record],
    integrity_suspect: bool = False,
) -> str:
    if integrity_suspect:
        return "INTEGRITY_SUSPECT"
    if not schedule:
        return "UNSCHEDULED"

    scheduled_minutes = (
        datetime.combine(datetime.today(), schedule["end_time"]) -
        datetime.combine(datetime.today(), schedule["start_time"])
    ).seconds // 60

    if scheduled_minutes == 0:
        return "UNKNOWN"

    pct = (minutes_present / scheduled_minutes) * 100
    threshold = schedule["min_attendance_pct"]

    if pct >= threshold:
        return "PRESENT"
    elif pct >= threshold * 0.5:
        return "PARTIAL"
    else:
        return "ABSENT"


async def lookup_user_id(pool: asyncpg.Pool, student_id: str) -> Optional[int]:
    row = await pool.fetchrow("SELECT id FROM users WHERE student_id = $1", student_id)
    return row["id"] if row else None


async def write_attendance_record(
    pool: asyncpg.Pool,
    username: str,
    schedule: Optional[asyncpg.Record],
    date: datetime,
    connect_dt: Optional[datetime],
    disconnect_dt: Optional[datetime],
    minutes_present: int,
    bytes_dl: float,
    bytes_ul: float,
    status: str,
    proxy_risk_score: float,
    ap_name: str,
) -> None:
    user_id = await lookup_user_id(pool, username)
    if not user_id:
        logger.warning("Unknown user_id for username=%s — skipping DB write", username)
        return

    schedule_id = schedule["id"] if schedule else None
    session_date = date.date() if isinstance(date, datetime) else date

    await pool.execute(
        """
        INSERT INTO attendance_sessions
            (student_id, schedule_id, date, connect_time, disconnect_time,
             minutes_present, bytes_downloaded_mb, bytes_uploaded_mb,
             status, proxy_risk_score, ap_name)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (student_id, schedule_id, date) DO UPDATE SET
            minutes_present     = EXCLUDED.minutes_present,
            bytes_downloaded_mb = EXCLUDED.bytes_downloaded_mb,
            bytes_uploaded_mb   = EXCLUDED.bytes_uploaded_mb,
            status              = EXCLUDED.status,
            proxy_risk_score    = EXCLUDED.proxy_risk_score,
            disconnect_time     = EXCLUDED.disconnect_time
        """,
        user_id, schedule_id, session_date,
        connect_dt, disconnect_dt, minutes_present,
        bytes_dl, bytes_ul, status, proxy_risk_score, ap_name,
    )


async def process_stop_event(pool: asyncpg.Pool, message: str) -> None:
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in stop event: %s", message)
        return

    username = data.get("username", "?")
    logger.info("Finalizing session for %s …", username)

    # Parse timestamps
    connect_dt = None
    disconnect_dt = None
    try:
        if data.get("connect_time"):
            connect_dt = datetime.fromisoformat(data["connect_time"])
        if data.get("disconnect_time"):
            disconnect_dt = datetime.fromisoformat(data["disconnect_time"])
    except (ValueError, TypeError):
        pass

    # Byte counters (stored as raw octets in session, already MB here)
    bytes_dl = float(data.get("bytes_downloaded_mb", 0.0))
    bytes_ul = float(data.get("bytes_uploaded_mb", 0.0))
    room_id = data.get("room_id")
    if isinstance(room_id, str):
        room_id = int(room_id) if room_id.lstrip("-").isdigit() else None
    ap_name = data.get("ap_name", "unknown")
    acct_session_time = data.get("acct_session_time")

    # Resolve matching schedule
    schedule = await resolve_schedule(pool, room_id, connect_dt)

    # Calculate presence
    minutes_present = calculate_minutes_present(connect_dt, disconnect_dt, acct_session_time)

    # Determine attendance status
    status = determine_status(minutes_present, schedule)

    # AI Focus Score
    duration_min = minutes_present or (acct_session_time // 60 if acct_session_time else 0)
    proxy_risk_score = score_session(bytes_dl, bytes_ul, float(duration_min))

    logger.info(
        "Finalized | user=%s schedule=%s minutes=%d status=%s score=%.4f",
        username,
        schedule["course_code"] if schedule else "N/A",
        minutes_present,
        status,
        proxy_risk_score,
    )

    # Write to PostgreSQL
    date_ref = connect_dt or datetime.utcnow()
    await write_attendance_record(
        pool=pool,
        username=username,
        schedule=schedule,
        date=date_ref,
        connect_dt=connect_dt,
        disconnect_dt=disconnect_dt,
        minutes_present=minutes_present,
        bytes_dl=bytes_dl,
        bytes_ul=bytes_ul,
        status=status,
        proxy_risk_score=proxy_risk_score,
        ap_name=ap_name,
    )


async def run():
    logger.info("Aura Finalizer starting …")
    pool = await get_db_pool()
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)
    logger.info("Subscribed to Redis channel: %s", CHANNEL)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await process_stop_event(pool, message["data"])
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await redis_client.aclose()
        await pool.close()
        logger.info("Finalizer shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(run())
