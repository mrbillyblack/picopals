"""Pet state + interaction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, pet_logic, schemas
from ..database import get_db

router = APIRouter(prefix="/api/pets", tags=["pets"])


def _require(state, user_id):
    if state is None:
        raise HTTPException(status_code=404, detail=f"no pet for user {user_id}")
    return state


@router.get("/{user_id}", response_model=schemas.PetResponse)
def get_pet(user_id: str, db: Session = Depends(get_db)):
    """The polling endpoint: returns the pet's fast-forwarded live condition."""
    state = _require(crud.get_simulated_state(db, user_id), user_id)
    return schemas.PetResponse(user_id=user_id, pet=pet_logic.public_view(state))


@router.post("/{user_id}/hatch", response_model=schemas.PetResponse)
def hatch(user_id: str, db: Session = Depends(get_db)):
    """Called by the frontend when the 60s hatch animation completes."""
    state = _require(crud.hatch_pet(db, user_id), user_id)
    return schemas.PetResponse(user_id=user_id, pet=pet_logic.public_view(state))


@router.post("/{user_id}/action", response_model=schemas.PetResponse)
def action(user_id: str, req: schemas.ActionRequest, db: Session = Depends(get_db)):
    try:
        state = crud.apply_action(db, user_id, req.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    state = _require(state, user_id)
    return schemas.PetResponse(user_id=user_id, pet=pet_logic.public_view(state))


@router.post("/{user_id}/name", response_model=schemas.PetResponse)
def set_name(user_id: str, req: schemas.NameRequest, db: Session = Depends(get_db)):
    state = _require(crud.set_name(db, user_id, req.name), user_id)
    return schemas.PetResponse(user_id=user_id, pet=pet_logic.public_view(state))


@router.post("/{user_id}/reset", response_model=schemas.PetResponse)
def reset(user_id: str, db: Session = Depends(get_db)):
    """Reset to a fresh egg (keeps the user's id + recovery code)."""
    state = _require(crud.reset_pet(db, user_id), user_id)
    return schemas.PetResponse(user_id=user_id, pet=pet_logic.public_view(state))
