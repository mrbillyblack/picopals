"""Runtime configuration, read from environment variables."""

from __future__ import annotations

import os


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://tama:tama_change_me@localhost:3306/picopals",
        )
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cors = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        self.cors_origins: list[str] = [o.strip() for o in cors.split(",") if o.strip()]
        # How long a live pet sits in Redis before falling back to MySQL.
        self.redis_ttl_seconds: int = int(os.getenv("REDIS_TTL_SECONDS", "86400"))


settings = Settings()
