"""
/ingest/radius — core RADIUS accounting endpoint.
"""
from __future__ import annotations

import json
import logging
from typing import Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ingestion.db import lookup_room_for_ap, lookup_user_id
from ingestion.models.session_event import (
    AcctStatusType,
    IntegritySuspectResponse,
    LiveSessionInfo,
    RadiusEvent,
    SessionFinalizedResponse,
    SessionOpenedResponse,
    SessionUpdatedResponse,
)
from ingestion.parsers.radius_parser import parse_radius_event
from session_manager.redis_client import (
    get_all_active_sessions,
    session_close,
    session_open,
    session_update,
)

logger = logging.getLogger("aura.ingestion")
router = APIRouter()


@router.post(
    "/ingest/radius",
    summary="Ingest a RADIUS Accounting event",
    response_model=Union[
        SessionOpenedResponse,
        SessionUpdatedResponse,
        SessionFinalizedResponse,
        IntegritySuspectResponse,
    ],
)
async def ingest_radius(raw: dict):
    """
    Accepts raw RADIUS Accounting packets (JSON key-value).
    Dispatches session open / update / close events to Redis.
    """
    try:
        event: RadiusEvent = parse_radius_event(raw)
    except Exception as exc:
        logger.warning("Failed to parse RADIUS event: %s | raw=%s", exc, raw)
        raise HTTPException(status_code=422, detail=str(exc))

    username = event.user_name
    ap_name = event.called_station_id

    # --- Integrity check (mac_clone_attempt scenario) ---
    if event.integrity_suspect:
        logger.warning("INTEGRITY_SUSPECT event for %s on %s", username, ap_name)
        return IntegritySuspectResponse(
            username=username,
            ap_name=ap_name,
            reason="User-Name / MAC pairing flagged as suspect by WLC",
        )

    # --- Route by Acct-Status-Type ---
    if event.acct_status_type == AcctStatusType.START:
        room_id = await lookup_room_for_ap(ap_name)
        connect_time = event.event_timestamp.isoformat() if event.event_timestamp else None
        await session_open(
            username=username,
            room_id=room_id,
            connect_time=connect_time,
            ap_name=ap_name,
        )
        logger.info("SESSION OPEN | user=%s ap=%s room=%s", username, ap_name, room_id)
        return SessionOpenedResponse(username=username, ap_name=ap_name, room_id=room_id)

    elif event.acct_status_type == AcctStatusType.INTERIM_UPDATE:
        await session_update(
            username=username,
            bytes_in=event.acct_input_octets or 0,
            bytes_out=event.acct_output_octets or 0,
        )
        logger.debug("SESSION UPDATE | user=%s dl=%.2fMB ul=%.2fMB",
                     username, event.bytes_downloaded_mb, event.bytes_uploaded_mb)
        return SessionUpdatedResponse(
            username=username,
            bytes_downloaded_mb=event.bytes_downloaded_mb,
            bytes_uploaded_mb=event.bytes_uploaded_mb,
        )

    elif event.acct_status_type == AcctStatusType.STOP:
        # Final byte counts override running totals
        await session_update(
            username=username,
            bytes_in=event.acct_input_octets or 0,
            bytes_out=event.acct_output_octets or 0,
        )
        session_data = await session_close(username)

        if session_data is None:
            logger.warning("STOP received for unknown session: %s", username)
            return SessionFinalizedResponse(
                username=username,
                minutes_present=None,
                attendance_status=None,
                proxy_risk_score=None,
            )

        # Publish finalization task to Redis (finalizer worker picks it up)
        import redis.asyncio as aioredis
        import os
        r = aioredis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        await r.publish(
            "aura:events:stop",
            json.dumps({
                **session_data,
                "acct_session_time": event.acct_session_time,
                "disconnect_time": event.event_timestamp.isoformat() if event.event_timestamp else None,
            }),
        )
        await r.aclose()

        logger.info("SESSION STOP | user=%s → queued for finalization", username)
        return SessionFinalizedResponse(
            username=username,
            minutes_present=None,   # calculated async by finalizer
            attendance_status=None,
            proxy_risk_score=None,
        )

    # Accounting-On / Accounting-Off — informational, no action needed
    return JSONResponse(content={"status": "acknowledged", "type": event.acct_status_type})


@router.get("/sessions/live", summary="Get all currently active sessions")
async def get_live_sessions():
    """Returns all sessions currently held in Redis."""
    sessions = await get_all_active_sessions()
    return {"active_count": len(sessions), "sessions": sessions}


@router.get("/health", summary="Liveness probe")
async def health():
    return {"status": "ok", "service": "aura-ingestion"}


@router.get("/sessions/finalized", summary="Get finalized attendance sessions")
async def get_finalized_sessions(limit: int = 100, offset: int = 0):
    """Query PostgreSQL for finalized attendance_sessions."""
    from ingestion.db import get_pool
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT
            a.id,
            u.student_id,
            u.name AS student_name,
            s.course_code,
            s.course_name,
            a.date,
            a.connect_time,
            a.disconnect_time,
            a.minutes_present,
            a.bytes_downloaded_mb,
            a.bytes_uploaded_mb,
            a.status,
            a.proxy_risk_score,
            a.ap_name
        FROM attendance_sessions a
        JOIN users u ON u.id = a.student_id
        JOIN schedules s ON s.id = a.schedule_id
        ORDER BY a.date DESC, a.connect_time DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset
    )
    return {"sessions": [dict(r) for r in rows]}


@router.get("/sessions/flagged", summary="Get sessions with high proxy_risk_score")
async def get_flagged_sessions(threshold: float = 0.75):
    """Query PostgreSQL for sessions flagged by the AI model."""
    from ingestion.db import get_pool
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT
            a.id,
            u.student_id,
            u.name AS student_name,
            s.course_code,
            a.date,
            a.minutes_present,
            a.bytes_downloaded_mb,
            a.bytes_uploaded_mb,
            a.status,
            a.proxy_risk_score,
            a.ap_name
        FROM attendance_sessions a
        JOIN users u ON u.id = a.student_id
        JOIN schedules s ON s.id = a.schedule_id
        WHERE a.proxy_risk_score >= $1
        ORDER BY a.proxy_risk_score DESC
        LIMIT 200
        """,
        threshold
    )
    return {"flagged": [dict(r) for r in rows]}
