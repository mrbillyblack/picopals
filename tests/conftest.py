"""Shared pytest fixtures.

We run the API against a throwaway SQLite database and an in-memory fake for
Redis, so the unit tests need neither MySQL nor a Redis server. Environment
variables are set *before* importing the app so its config picks them up.
"""

import json
import os

# Must be set before `app.*` is imported (config reads env at import time).
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_picopals.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
# Disable rate limiting so the suite isn't throttled and needs no Redis store.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import redis_client  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Replace the Redis helpers with an in-process dict so crud/routers work
    without a live Redis. json round-trips mimic real (de)serialization."""
    store: dict[str, str] = {}

    def save(uid, state):
        store[uid] = json.dumps(state)

    def load(uid):
        raw = store.get(uid)
        return json.loads(raw) if raw else None

    def delete(uid):
        store.pop(uid, None)

    monkeypatch.setattr(redis_client, "save_pet", save)
    monkeypatch.setattr(redis_client, "load_pet", load)
    monkeypatch.setattr(redis_client, "delete_pet", delete)
    yield


@pytest.fixture()
def client():
    """Fresh schema per test for isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
