from fastapi_users import schemas
import uuid
from pydantic import BaseModel
from typing import List, Optional

# Role schema for API responses
class RoleRead(BaseModel):
    id: uuid.UUID
    name: str

# Schema for creating a new user (inherits email & password validation)
class UserCreate(schemas.BaseUserCreate):
    roles: Optional[List[uuid.UUID]] = []  # allow assigning roles at creation

# Schema for reading user data (includes nested roles)
class UserRead(schemas.BaseUser[uuid.UUID]):
    roles: List[RoleRead] = []

# Schema for updating user data (all fields optional)
class UserUpdate(schemas.BaseUserUpdate):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    roles: Optional[List[uuid.UUID]] = None

