from fastapi_users import schemas

class RoleRead(schemas.BaseModel):
    id: uuid.UUID
    name: str

class UserCreate(schemas.UC):
    # inherits email & password
    pass

class UserRead(schemas.UR):
    id: uuid.UUID
    email: str
    is_active: bool
    is_superuser: bool
    roles: list[RoleRead]

class UserUpdate(schemas.UU):
    is_active: Optional[bool]
    is_superuser: Optional[bool]
    roles: Optional[list[uuid.UUID]]
