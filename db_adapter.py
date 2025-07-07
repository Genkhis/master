from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from database import get_async_db
from models import User


async def get_user_db(
    # ✅ pass the *function*, NOT get_async_db()!
    session: AsyncSession = Depends(get_async_db),
):
    """
    Provide FastAPI-Users with an AsyncSession-backed user DB adapter.
    """
    yield SQLAlchemyUserDatabase(session, User)