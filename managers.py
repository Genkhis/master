# managers.py
from uuid import UUID
from fastapi import Depends, Request
from fastapi_users import BaseUserManager
from fastapi_users.db import SQLAlchemyUserDatabase
from database import SessionLocal
from models import User

SECRET = "…your JWT secret…"

class UserManager(BaseUserManager[User, UUID]):
    user_db_model = User
    reset_password_token_secret = SECRET
    verification_token_secret   = SECRET

    async def on_after_register(self, user: User, request: Request | None = None):
        # optional hook
        ...

# dependency that *yields* an instance of your manager
async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),  # your existing adapter
) -> UserManager:
    yield UserManager(user_db)
