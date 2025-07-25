﻿from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from database import get_async_db
from models import User


async def get_user_db(
    session: AsyncSession = Depends(get_async_db),   # ← no parentheses
):
    yield SQLAlchemyUserDatabase(session, User)