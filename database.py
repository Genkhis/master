# database.py  – central DB plumbing
import os
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine.url import make_url

# parse the sync URL and swap the driver name
sync_url = make_url(os.environ["DATABASE_URL"])
async_url = sync_url.set(drivername="postgresql+asyncpg")

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
    async_url,
    future=True,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},  # mirror your sync SSL settings
)
async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# now you can safely:
# from database import async_session
