"""
database.py – central DB plumbing (sync + async)

▪  Call `get_db()`      → yields a classic synchronous Session
▪  Call `get_async_db()` → yields an AsyncSession (needed by FastAPI-Users)
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# --------------------------------------------------------------------------- #
# 0. Environment
# --------------------------------------------------------------------------- #
if Path(".env").exists():
    # Only load if present so prod ENV vars still win
    from dotenv import load_dotenv

    load_dotenv(override=True)

DATABASE_URL_SYNC = os.getenv("DATABASE_URL")
if not DATABASE_URL_SYNC:
    raise RuntimeError("DATABASE_URL not set")

# --------------------------------------------------------------------------- #
# 1. URLs – derive async URL from sync one to avoid duplication
# --------------------------------------------------------------------------- #
sync_url = make_url(DATABASE_URL_SYNC)
async_url = sync_url.set(drivername="postgresql+asyncpg")

# --------------------------------------------------------------------------- #
# 2. Engines
# --------------------------------------------------------------------------- #
engine = create_engine(
    str(sync_url),
    future=True,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)

async_engine = create_async_engine(
    str(async_url),
    future=True,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)

# --------------------------------------------------------------------------- #
# 3. Session factories
# --------------------------------------------------------------------------- #
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declarative base for ORM models
Base = declarative_base()

# --------------------------------------------------------------------------- #
# 4. FastAPI dependencies
# --------------------------------------------------------------------------- #
def get_db():
    """Yield a synchronous SQLAlchemy Session (blocking)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db():
    """Yield an *AsyncSession* for non-blocking DB work."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
