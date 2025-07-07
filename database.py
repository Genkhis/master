import os
from pathlib import Path
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# --------------------------------------------------------------------------- #
# 1. Environment
# --------------------------------------------------------------------------- #
# Load .env in dev; prod should rely on real env vars
if Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

DATABASE_URL_SYNC = os.getenv("DATABASE_URL")
if not DATABASE_URL_SYNC:
    raise RuntimeError("DATABASE_URL not set")

# --------------------------------------------------------------------------- #
# 2. URL objects (password kept intact)
# --------------------------------------------------------------------------- #
sync_url = make_url(DATABASE_URL_SYNC)
async_url = sync_url.set(drivername="postgresql+asyncpg")

# --------------------------------------------------------------------------- #
# 3. Engines
# --------------------------------------------------------------------------- #
engine = create_engine(
    sync_url,                    # URL object → password NOT redacted
    future=True,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)

async_engine = create_async_engine(
    async_url,                   # asyncpg driver, password intact
    future=True,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)

# --------------------------------------------------------------------------- #
# 4. Session factories
# --------------------------------------------------------------------------- #
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declarative base for your ORM models
Base = declarative_base()

# --------------------------------------------------------------------------- #
# 5. FastAPI dependencies
# --------------------------------------------------------------------------- #
def get_db():
    """Yield a blocking (sync) Session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db():
    """Yield an AsyncSession (non-blocking)."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()