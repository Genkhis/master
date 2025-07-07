from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase

# ─── import your existing adapter function ───
from backend_fastapi import get_user_db    # ← adjust the module path as needed

from models import User
from fastapi_users import BaseUserManager
from fastapi import Request
from uuid import UUID

SECRET = "…your JWT secret…"

class UserManager(BaseUserManager[User, UUID]):
    user_db_model = User
    reset_password_token_secret = SECRET
    verification_token_secret   = SECRET

    async def on_after_register(self, user: User, request: Request | None = None):
        # optional hook
        ...

async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> UserManager:
    yield UserManager(user_db)
