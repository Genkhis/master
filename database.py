# database.py  – central DB plumbing
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ───────────────────────────────────────────────────────────
# 1) load local .env for dev; prod/render injects real ENV vars
# ───────────────────────────────────────────────────────────
if Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

# ───────────────────────────────────────────────────────────
# 2) SQLAlchemy base + engine factory
# ───────────────────────────────────────────────────────────
Base = declarative_base()

def get_engine():
    url = os.getenv("DATABASE_URL")          # pooled URL in prod
    if not url:
        raise RuntimeError("DATABASE_URL not set")

    return create_engine(
        url,
        future=True,                         # SQLAlchemy 2-style
        pool_pre_ping=True,                 # survive PgBouncer kicks
        connect_args={"sslmode": "require"},# Neon requires SSL
    )

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# ───────────────────────────────────────────────────────────
# NOTE: Removed the import of Article, Supplier, ArticlePrice
#       to break the circular dependency between database.py
#       and models.py.
# ───────────────────────────────────────────────────────────
