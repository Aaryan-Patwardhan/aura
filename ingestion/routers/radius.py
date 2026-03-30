"""
/ingest/radius — core RADIUS accounting endpoint.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import ValidationError

from common.db import lookup_room_for_ap, lookup_user_id
from ingestion.limiter import limiter
from ingestion.models.session_event import (
    AcctStatusType,
    IntegritySuspectResponse,
    RadiusEvent,
    SessionFinalizedResponse,
    SessionOpenedResponse,
    SessionUpdatedResponse,
)
from ingestion.parsers.radius_parser import parse_radius_event
from session_manager.redis_client import (
    get_all_active_sessions,
    get_session,
    session_close,
    session_open,
    session_update,
    _get_redis,
)

logger = logging.getLogger("aura.ingestion")

import hmac

API_KEY = os.environ.get("AURA_API_KEY", "dev_secret_key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not hmac.compare_digest(api_key, API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

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
    dependencies=[Security(verify_api_key)],
)
@limiter.limit("100/minute")
async def ingest_radius(request: Request, raw: dict):
    """
    Accepts raw RADIUS Accounting packets (JSON key-value).
    Dispatches session open / update / close events to Redis.
    """
    try:
        event: RadiusEvent = parse_radius_event(raw)
    except (ValueError, ValidationError) as exc:
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
        # Only update byte counters if the WLC actually sent them.
        # RFC 2866 permits omitting byte counters from Interim-Updates.
        # Passing 0 would corrupt the running total in Redis (HSET overwrites).
        if event.acct_input_octets is not None and event.acct_output_octets is not None:
            await session_update(
                username=username,
                bytes_in=event.bytes_downloaded_mb,
                bytes_out=event.bytes_uploaded_mb,
            )
            logger.debug("SESSION UPDATE | user=%s dl=%.2fMB ul=%.2fMB",
                         username, event.bytes_downloaded_mb, event.bytes_uploaded_mb)
        else:
            logger.debug("SESSION UPDATE (no byte counters) | user=%s — keeping existing Redis values", username)
            session = await get_session(username)
            if session:
                return SessionUpdatedResponse(
                    username=username,
                    bytes_downloaded_mb=session["bytes_downloaded_mb"],
                    bytes_uploaded_mb=session["bytes_uploaded_mb"],
                )

        return SessionUpdatedResponse(
            username=username,
            bytes_downloaded_mb=event.bytes_downloaded_mb,
            bytes_uploaded_mb=event.bytes_uploaded_mb,
        )

    elif event.acct_status_type == AcctStatusType.STOP:
        # Final byte counts override running totals in Redis.
        # Stop packets always include byte counters (RFC 2866 §4.1).
        await session_update(
            username=username,
            bytes_in=event.bytes_downloaded_mb,
            bytes_out=event.bytes_uploaded_mb,
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

        # Publish finalization task to Redis Stream (finalizer worker consumes it)
        r = _get_redis()
        # Ensure ID limit prevents infinite growth if consumer dies
        await r.xadd(
            "aura:streams:stop",
            {
                "data": json.dumps({
                    **session_data,
                    "acct_session_time": event.acct_session_time,
                    "disconnect_time": event.event_timestamp.isoformat() if event.event_timestamp else None,
                })
            },
            maxlen=10000,
            approximate=True
        )

        logger.info("SESSION STOP | user=%s → queued for finalization", username)
        return SessionFinalizedResponse(
            username=username,
            minutes_present=None,   # calculated async by finalizer
            attendance_status=None,
            proxy_risk_score=None,
        )

    # Accounting-On / Accounting-Off — informational, no action needed
    return JSONResponse(content={"status": "acknowledged", "type": event.acct_status_type})


@router.get("/sessions/live", summary="Get all currently active sessions", dependencies=[Security(verify_api_key)])
async def get_live_sessions():
    """Returns all sessions currently held in Redis."""
    sessions = await get_all_active_sessions()
    return {"active_count": len(sessions), "sessions": sessions}


@router.get("/health", summary="Liveness probe")
async def health():
    return {"status": "ok", "service": "aura-ingestion"}


@router.get("/sessions/finalized", summary="Get finalized attendance sessions", dependencies=[Security(verify_api_key)])
async def get_finalized_sessions(limit: int = 100, offset: int = 0):
    """Query PostgreSQL for finalized attendance_sessions."""
    
    # Enforce safe bounds
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)

    from common.db import get_pool
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
        LEFT JOIN schedules s ON s.id = a.schedule_id
        ORDER BY a.date DESC, a.connect_time DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset
    )
    return {"sessions": [dict(r) for r in rows]}


@router.get("/sessions/flagged", summary="Get sessions with high proxy_risk_score", dependencies=[Security(verify_api_key)])
async def get_flagged_sessions(threshold: float = 0.75):
    """Query PostgreSQL for sessions flagged by the AI model."""
    from common.db import get_pool
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
        LEFT JOIN schedules s ON s.id = a.schedule_id
        WHERE a.proxy_risk_score >= $1
        ORDER BY a.proxy_risk_score DESC
        LIMIT 200
        """,
        threshold
    )
    return {"flagged": [dict(r) for r in rows]}


@router.get("/metadata/rooms", summary="Get physical room configurations", dependencies=[Security(verify_api_key)])
async def get_rooms_metadata():
    from common.db import get_pool
    pool = await get_pool()
    rows = await pool.fetch("SELECT id, room_number as name, capacity FROM rooms ORDER BY id ASC")
    return {"rooms": [dict(r) for r in rows]}
