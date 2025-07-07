from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from database import get_async_db      # <-- NEW import
from models import User


async def get_user_db(
    session: AsyncSession = Depends(get_async_db),   # <-- async injection
) -> SQLAlchemyUserDatabase:
    """
    Provides a SQLAlchemyUserDatabase bound to an AsyncSession and the User model.
    """
    # Positional args to satisfy old & new versions
    yield SQLAlchemyUserDatabase(session, User)
