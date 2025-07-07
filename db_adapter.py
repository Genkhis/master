from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from database import SessionLocal, get_db    # your normal get_db→Session
from models import User     

async def get_user_db(
    session: Session = Depends(get_db),
) -> SQLAlchemyUserDatabase:
    """
    Yields a SQLAlchemyUserDatabase instance bound to your User model.
    """
    yield SQLAlchemyUserDatabase(User, session)

