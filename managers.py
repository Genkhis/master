# managers.py

from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, Request
from fastapi_users import BaseUserManager
from fastapi_users.db import SQLAlchemyUserDatabase

from db_adapter import get_user_db  # your existing adapter, no circular import
from models import User

# Use the same secret as your JWT strategy
SECRET = "your‐jwt‐secret‐here"


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
        Called after a new user successfully registers.
        You can send a welcome email here, etc.
        """
        # e.g. send_welcome_email(user.email)
        ...


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    """
    Dependency that yields a UserManager instance for FastAPI-Users.
    """
    yield UserManager(user_db)
