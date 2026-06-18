"""SQLAlchemy ORM models (MySQL durable storage)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)  # UUID4
    recovery_code = Column(String(32), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    pet = relationship(
        "Pet", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Pet(Base):
    __tablename__ = "pets"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # The entire simulation state lives in one JSON column. This keeps the
    # schema stable as gameplay evolves; Redis holds the live copy.
    state = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="pet")
