# schemas.py
import uuid
from typing import List, Optional

from pydantic import BaseModel, EmailStr
from fastapi_users import schemas


# ────────────────────────────
# Role DTO (if you ever expose it)
# ────────────────────────────
class RoleRead(BaseModel):
    id: uuid.UUID
    name: str


# ────────────────────────────
# User – CREATE
# ────────────────────────────
class UserCreate(schemas.BaseUserCreate):
    roles: Optional[List[uuid.UUID]] = []  # allow role IDs at creation


# ────────────────────────────
# User – READ  (⚠️ no roles; avoids lazy-load / MissingGreenlet)
# ────────────────────────────
class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool

    class Config:
        from_attributes = True


# ────────────────────────────
# User – PATCH / PUT
# ────────────────────────────
class UserUpdate(schemas.BaseUserUpdate):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    roles: Optional[List[uuid.UUID]] = None
