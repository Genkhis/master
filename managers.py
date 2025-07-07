# managers.py
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from db_adapter import get_user_db    # ← no more circular import
from fastapi_users import BaseUserManager
from fastapi import Request
from models import User
from uuid import UUID

SECRET = "your‐jwt‐secret‐here"

class UserManager(BaseUserManager[User, UUID]):
    user_db_model = User
    reset_password_token_secret = SECRET
    verification_token_secret   = SECRET

    async def on_after_register(self, user: User, request: Request | None = None):
        # optional
        ...

async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> UserManager:
    yield UserManager(user_db)
