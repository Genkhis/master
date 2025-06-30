"""
Alembic migration runner – Neon-ready, env-var driven
"""
from pathlib import Path
import os
from database import Base
from alembic import context
from logging.config import fileConfig
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# ── logging ────────────────────────────────────────────────────────
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# ── dev .env loader ────────────────────────────────────────────────
if Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

DATABASE_ADMIN_URL = os.environ["DATABASE_ADMIN_URL"]

# ── metadata import: **only models, no FastAPI side-effects** ──────
from database import Base      # <-- you'll create this in step 2
target_metadata = Base.metadata

# ── runners ────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_ADMIN_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(
        DATABASE_ADMIN_URL,
        poolclass=NullPool,
        connect_args={"sslmode": "require"},
    )
    with engine.connect() as connection:
        context.configure(connection=connection,
                          target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
