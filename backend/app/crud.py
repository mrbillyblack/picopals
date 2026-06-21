"""Persistence orchestration.

Read path:  Redis (hot) -> fall back to MySQL (durable) -> simulate -> Redis.
Write path: mutate state -> Redis + MySQL together.

Keeping this in one module means the routers stay thin and the Redis/MySQL
coordination lives in a single, testable place.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from . import models, pet_logic, redis_client

# Human-friendly recovery code, e.g. "WARM-FROG-7Q2KX9MN". Avoids ambiguous
# chars. The random suffix carries the entropy: 32^8 ≈ 1.1e12 combinations, so
# even with the per-IP rate limit lifted it's infeasible to brute force (vs the
# old 4-char suffix ≈ 1e6, which was guessable in hours).
_ADJECTIVES = ["WARM", "COZY", "JOLLY", "FUZZY", "SUNNY", "MINTY", "PERKY", "ZIPPY"]
_NOUNS = ["FROG", "PUP", "KITTY", "BUNNY", "EGG", "STAR", "MOON", "BEAN"]
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I/O/0/1
_SUFFIX_LEN = 8


def generate_recovery_code() -> str:
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(_SUFFIX_LEN))
    return f"{secrets.choice(_ADJECTIVES)}-{secrets.choice(_NOUNS)}-{suffix}"


def _unique_recovery_code(db: Session) -> str:
    for _ in range(10):
        code = generate_recovery_code()
        exists = db.query(models.User).filter_by(recovery_code=code).first()
        if not exists:
            return code
    raise RuntimeError("could not allocate a unique recovery code")


def create_user_with_egg(db: Session) -> tuple[models.User, dict]:
    """Create a brand new user + a fresh egg pet (Redis + MySQL)."""
    user = models.User(id=str(uuid.uuid4()), recovery_code=_unique_recovery_code(db))
    state = pet_logic.new_egg()
    pet = models.Pet(user_id=user.id, state=state)
    db.add(user)
    db.add(pet)
    db.commit()
    redis_client.save_pet(user.id, state)
    return user, state


def get_user(db: Session, user_id: str) -> Optional[models.User]:
    return db.query(models.User).filter_by(id=user_id).first()


def get_user_by_code(db: Session, recovery_code: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter_by(recovery_code=recovery_code.strip().upper())
        .first()
    )


def _persist(db: Session, user_id: str, state: dict) -> None:
    """Write live state to both stores."""
    redis_client.save_pet(user_id, state)
    pet = db.query(models.Pet).filter_by(user_id=user_id).first()
    if pet is None:
        pet = models.Pet(user_id=user_id, state=state)
        db.add(pet)
    else:
        pet.state = state
    db.commit()


def load_state(db: Session, user_id: str) -> Optional[dict]:
    """Load the live pet state, preferring Redis and rehydrating from MySQL if
    Redis is cold (e.g. after a restart). Returns ``None`` if no such user."""
    state = redis_client.load_pet(user_id)
    if state is None:
        pet = db.query(models.Pet).filter_by(user_id=user_id).first()
        if pet is None:
            return None
        state = dict(pet.state)
        redis_client.save_pet(user_id, state)
    return state


def get_simulated_state(db: Session, user_id: str) -> Optional[dict]:
    """Load + fast-forward decay + persist. The canonical 'read current pet'."""
    state = load_state(db, user_id)
    if state is None:
        return None
    pet_logic.simulate(state)
    _persist(db, user_id, state)
    return state


def hatch_pet(db: Session, user_id: str) -> Optional[dict]:
    state = load_state(db, user_id)
    if state is None:
        return None
    pet_logic.simulate(state)
    pet_logic.hatch(state)
    _persist(db, user_id, state)
    return state


def apply_action(db: Session, user_id: str, action: str) -> Optional[dict]:
    state = load_state(db, user_id)
    if state is None:
        return None
    pet_logic.apply_action(state, action)  # raises ValueError on bad action
    _persist(db, user_id, state)
    return state


def set_name(db: Session, user_id: str, name: str) -> Optional[dict]:
    state = load_state(db, user_id)
    if state is None:
        return None
    state["name"] = name.strip()[:16]
    _persist(db, user_id, state)
    return state


def reset_pet(db: Session, user_id: str) -> Optional[dict]:
    """Lay a fresh egg for an existing user (keeps their id/recovery code)."""
    if get_user(db, user_id) is None:
        return None
    state = pet_logic.new_egg()
    _persist(db, user_id, state)
    return state
