# database.py  – central DB plumbing
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

if Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

DATABASE_URL_SYNC  = os.getenv("DATABASE_URL")
if not DATABASE_URL_SYNC:
    raise RuntimeError("DATABASE_URL not set")
# use the same URL but with asyncpg for async
DATABASE_URL_ASYNC = DATABASE_URL_SYNC.replace("postgresql://", "postgresql+asyncpg://")

# sync engine & session
Base   = declarative_base()
engine = create_engine(
    DATABASE_URL_SYNC,
    future=True,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# async engine & session
async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    future=True,
    pool_pre_ping=True,
)
async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# now you can safely:
# from database import async_session
