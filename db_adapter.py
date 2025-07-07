from fastapi import Depends
from sqlalchemy.orm import Session            # consider AsyncSession later
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from database import get_db
from models import User


async def get_user_db(
    session: Session = Depends(get_db),        # inject one DB session per request
) -> SQLAlchemyUserDatabase:
    """
    Provide a SQLAlchemyUserDatabase bound to the current session and User model.

    NOTE:
    1.  Pass the arguments POSITIONALLY – session first, model second – to satisfy
        both old and new fastapi-users-db-sqlalchemy versions.
    2.  If you upgrade to a release that supports keyword args, feel free to switch
        to `SQLAlchemyUserDatabase(session=session, user_model=User)`.
    """
    yield SQLAlchemyUserDatabase(session, User)
