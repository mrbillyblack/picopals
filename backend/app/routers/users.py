"""User identity + pet recovery endpoints."""

# NOTE: no `from __future__ import annotations` here — slowapi's @limiter.limit
# wraps the endpoints, and stringized annotations would fail to resolve
# (e.g. schemas.RecoverRequest) when FastAPI builds the routes.

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import crud, pet_logic, schemas
from ..database import get_db
from ..ratelimit import limiter

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=schemas.UserCreateResponse, status_code=201)
@limiter.limit("10/hour;30/day")
def create_user(request: Request, db: Session = Depends(get_db)):
    """First-visit handshake: mint a unique user id + recovery code and lay an
    egg. The frontend stores the id in localStorage.

    Rate-limited per IP so a single client can't mass-create users to exhaust
    MySQL/Redis storage."""
    user, state = crud.create_user_with_egg(db)
    return schemas.UserCreateResponse(
        user_id=user.id,
        recovery_code=user.recovery_code,
        pet=pet_logic.public_view(state),
    )


@router.post("/recover", response_model=schemas.RecoverResponse)
@limiter.limit("5/minute;20/hour;100/day")
def recover(request: Request, req: schemas.RecoverRequest, db: Session = Depends(get_db)):
    """Restore a pet on a new device/IP or after cleared cookies, using the
    recovery code the user saved.

    Tightly rate-limited per IP: this is the brute-force target, so we cap
    guesses hard in addition to the wide recovery-code keyspace."""
    user = crud.get_user_by_code(db, req.recovery_code)
    if user is None:
        raise HTTPException(status_code=404, detail="recovery code not found")
    state = crud.get_simulated_state(db, user.id)
    return schemas.RecoverResponse(
        user_id=user.id,
        recovery_code=user.recovery_code,
        pet=pet_logic.public_view(state),
    )


@router.get("/{user_id}", response_model=schemas.RecoverResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Used on reload to confirm a stored id is still valid and fetch its code."""
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    state = crud.get_simulated_state(db, user.id)
    return schemas.RecoverResponse(
        user_id=user.id,
        recovery_code=user.recovery_code,
        pet=pet_logic.public_view(state),
    )
