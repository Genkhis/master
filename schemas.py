from fastapi_users import schemas
import uuid
from typing import List, Optional

# Role schema for API responses
class RoleRead(schemas.BaseModel):
    id: uuid.UUID
    name: str

# Schema for creating a new user (inherits email & password validation)
class UserCreate(schemas.UC):
    roles: Optional[List[uuid.UUID]] = []  # allow assigning roles at creation

# Schema for reading user data (includes roles as nested objects)
class UserRead(schemas.UR):
    id: uuid.UUID
    email: str
    is_active: bool
    is_superuser: bool
    roles: List[RoleRead]

# Schema for updating user data (all fields optional)
class UserUpdate(schemas.UU):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    roles: Optional[List[uuid.UUID]] = None
