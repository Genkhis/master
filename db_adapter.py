# db_adapter.py
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from database import SessionLocal
from models import User

def get_user_db():
    """
    Adapter for fastapi-users. Yields a SQLAlchemyUserDatabase
    bound to our User model and SessionLocal.
    """
    yield SQLAlchemyUserDatabase(User, SessionLocal())
