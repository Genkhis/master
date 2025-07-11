# managers.py
from typing import AsyncGenerator, Optional
from uuid import UUID
import os

from fastapi import Depends, Request
from fastapi_users import BaseUserManager
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from db_adapter import get_user_db
from models import User



SECRET = os.getenv("JWT_SECRET", "change-me")  # keep as str, do not .encode()

class UserManager(BaseUserManager[User, UUID]):
    """
    Manages user authentication, password resets, and email verifications.
    """
    user_db_model = User
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        """
        Hook that runs right after a successful registration.
        You can send a welcome email, log analytics, etc.
        """
        ...

# ---------------------------------------------------------------------------
# Dependency factory that FastAPI-Users will call
# ---------------------------------------------------------------------------
async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)
