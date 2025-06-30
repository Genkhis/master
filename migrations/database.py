# ─── database.py  (NEW small helper) ────────────────────────────────
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine() -> "Engine":
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return create_engine(
        url,
        future=True,                 # SQLAlchemy 2-style
        pool_pre_ping=True,          # survive PgBouncer kicks
        connect_args={"sslmode": "require"},
    )

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
