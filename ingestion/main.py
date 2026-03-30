"""
Aura Ingestion Server — FastAPI application factory.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ingestion.db import close_pool, get_pool
from ingestion.routers.radius import router as radius_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("aura.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm the DB pool. Shutdown: close it."""
    logger.info("Aura Ingestion starting — warming DB connection pool …")
    await get_pool()
    logger.info("DB pool ready.")
    yield
    logger.info("Aura Ingestion shutting down — closing DB pool …")
    await close_pool()


app = FastAPI(
    title="Aura Ingestion API",
    description=(
        "Passive attendance intelligence — receives RADIUS Accounting events "
        "from the campus WLC and dispatches session state to Redis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(radius_router, tags=["RADIUS"])


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "ingestion.main:app",
        host=os.environ.get("INGESTION_HOST", "0.0.0.0"),
        port=int(os.environ.get("INGESTION_PORT", 8000)),
        reload=False,
        log_level="info",
    )
