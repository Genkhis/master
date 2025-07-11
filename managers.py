# managers.py
from typing import AsyncGenerator, Optional
from uuid import UUID
import os

from fastapi import Depends, Request
from fastapi_users.manager import BaseUserManager, UUIDIDMixin  # <-- MIXIN here
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from db_adapter import get_user_db
from models import User

# ──────────────────────────────────────────────────────────────
SECRET = os.getenv("JWT_SECRET", "change-me")  # same string everywhere
# ──────────────────────────────────────────────────────────────

class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """
    Custom manager that supports UUID primary keys via UUIDIDMixin.
    The mixin implements `parse_id()`, eliminating NotImplementedError.
    """
    user_db_model = User
    reset_password_token_secret = SECRET
    verification_token_secret   = SECRET

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        # Hook (optional): send welcome mail, analytics, etc.
        pass

# Dependency factory used in backend_fastapi.py
async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)
