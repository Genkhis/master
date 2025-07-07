from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from database import get_db
from models import User


async def get_user_db(
    session: Session = Depends(get_db),
) -> SQLAlchemyUserDatabase:
    """
    Yields a SQLAlchemyUserDatabase instance bound to your User model.
    """
    # NOTE: pass the session first, then the model (or use keywords like here)
    yield SQLAlchemyUserDatabase(session=session, user_db_model=User)
