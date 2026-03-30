"""
Aura Ingestion Server — FastAPI application factory.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from ingestion.limiter import limiter

from common.db import close_pool, get_pool
from ingestion.routers.radius import router as radius_router
from session_manager.redis_client import close_redis, init_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("aura.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm the DB pool. Shutdown: close it."""
    logger.info("Aura Ingestion starting — warming DB and Redis connection pools …")
    await get_pool()
    init_redis()
    logger.info("DB and Redis pools ready.")
    yield
    logger.info("Aura Ingestion shutting down — closing connection pools …")
    await close_pool()
    await close_redis()


app = FastAPI(
    title="Aura Ingestion API",
    description=(
        "Passive attendance intelligence — receives RADIUS Accounting events "
        "from the campus WLC and dispatches session state to Redis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 2_097_152: # 2MB
            return JSONResponse({"detail": "Payload Too Large"}, status_code=413)
    return await call_next(request)

cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(radius_router, tags=["RADIUS"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ingestion.main:app",
        host=os.environ.get("INGESTION_HOST", "0.0.0.0"),
        port=int(os.environ.get("INGESTION_PORT", 8000)),
        reload=False,
        log_level="info",
    )
