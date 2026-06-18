"""Pydantic request/response models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class UserCreateResponse(BaseModel):
    user_id: str
    recovery_code: str
    pet: dict


class RecoverRequest(BaseModel):
    recovery_code: str


class RecoverResponse(BaseModel):
    user_id: str
    recovery_code: str
    pet: dict


class ActionRequest(BaseModel):
    action: str


class NameRequest(BaseModel):
    name: str


class PetResponse(BaseModel):
    user_id: str
    pet: dict


class HealthResponse(BaseModel):
    status: str
    redis: bool
    mysql: bool
