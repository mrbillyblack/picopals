"""Shared rate limiter (slowapi).

Lives in its own module so both main.py and the routers can import the same
``limiter`` instance without a circular import. State is kept in Redis so limits
hold across multiple backend replicas; in tests it's disabled and uses an
in-memory store so no Redis is required.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from .config import settings


def get_client_ip(request: Request) -> str:
    """Real client IP even behind Caddy/nginx. The proxy sets X-Forwarded-For;
    we take the left-most entry (the original client)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_client_ip,
    # Generous global ceiling per IP — a DoS guard, not normal-use throttling.
    default_limits=["200/minute", "2000/hour"],
    storage_uri=settings.redis_url if settings.rate_limit_enabled else "memory://",
    enabled=settings.rate_limit_enabled,
)
