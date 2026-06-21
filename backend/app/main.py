"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from . import models  # noqa: F401  (ensure models are registered)
from .config import settings
from .database import Base, engine, get_db
from .ratelimit import limiter
from .redis_client import get_redis
from .routers import pets, users
from .schemas import HealthResponse

logger = logging.getLogger("uvicorn.error")


def _wait_for_db(retries: int = 30, delay: float = 2.0) -> None:
    """Wait for MySQL to accept TCP connections.

    On a cold start the official MySQL image initialises the database with
    networking disabled, so the server isn't reachable over TCP for a while.
    Rather than crash, retry until it's ready (or give up after ~retries*delay).
    """
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            if attempt == retries:
                raise
            logger.warning(
                "Database not ready (attempt %d/%d); retrying in %.0fs…",
                attempt, retries, delay,
            )
            time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _wait_for_db()
    # init.sql also creates these, but this makes local (non-docker) runs work.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="picopals API",
    version="1.0.0",
    lifespan=lifespan,
    # Hide the API schema/docs unless explicitly enabled (dev only).
    docs_url="/api/docs" if settings.enable_docs else None,
    redoc_url="/api/redoc" if settings.enable_docs else None,
    openapi_url="/api/openapi.json" if settings.enable_docs else None,
)

# Rate limiting: register the limiter, a 429 handler, and the middleware that
# enforces the global default limits on every request.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS added last so it stays outermost (even 429s get CORS headers).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(pets.router)


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    redis_ok = True
    try:
        get_redis().ping()
    except Exception:
        redis_ok = False

    mysql_ok = True
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
    except Exception:
        mysql_ok = False

    status = "ok" if redis_ok and mysql_ok else "degraded"
    return HealthResponse(status=status, redis=redis_ok, mysql=mysql_ok)
