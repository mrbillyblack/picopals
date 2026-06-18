"""Redis access for live pet state.

Redis is the hot store: it holds the JSON snapshot of each pet's current
condition keyed by user id, so reads are fast and the simulation can be
fast-forwarded on demand. MySQL remains the durable source of truth.
"""

from __future__ import annotations

import json
from typing import Optional

import redis

from .config import settings

_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def _key(user_id: str) -> str:
    return f"pet:{user_id}"


def load_pet(user_id: str) -> Optional[dict]:
    raw = get_redis().get(_key(user_id))
    return json.loads(raw) if raw else None


def save_pet(user_id: str, state: dict) -> None:
    get_redis().set(
        _key(user_id), json.dumps(state), ex=settings.redis_ttl_seconds
    )


def delete_pet(user_id: str) -> None:
    get_redis().delete(_key(user_id))
