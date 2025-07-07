# db_adapter.py
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from models import User
from database import SessionLocal

def get_user_db():
    db = SessionLocal()
    try:
        yield SQLAlchemyUserDatabase(User, db)
    finally:
        db.close()
