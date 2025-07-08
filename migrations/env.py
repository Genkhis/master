"""
Alembic migration runner – Neon-ready, env-var driven
Creates ONLY the auth tables (users, roles, roles_users). Existing
article/supplier tables are left untouched.
"""
from pathlib import Path
import os

from alembic import context
from logging.config import fileConfig
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# ────────────────────────────────
# 1) Logging
# ────────────────────────────────
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# ────────────────────────────────
# 2) Load .env for local dev
# ────────────────────────────────
if Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

DATABASE_ADMIN_URL = os.environ["DATABASE_ADMIN_URL"]

# ────────────────────────────────
# 3) Model metadata
# ────────────────────────────────
from database import Base                   # <- imports models
target_metadata = Base.metadata

# ────────────────────────────────
# 4) include_object filter
#    → Alembic will *only* generate DDL
#      for the auth tables / indexes.
# ────────────────────────────────
AUTH_TABLES = {"users", "roles", "roles_users"}

def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in AUTH_TABLES:
        return True
    if type_ == "index" and any(name.startswith(f"ix_{t}_") for t in AUTH_TABLES):
        return True
    # skip everything else (no CREATE / DROP)
    return False

# ────────────────────────────────
# 5) Offline migration (SQL script)
# ────────────────────────────────
def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_ADMIN_URL,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# ────────────────────────────────
# 6) Online migration (direct)
# ────────────────────────────────
def run_migrations_online() -> None:
    engine = create_engine(
        DATABASE_ADMIN_URL,
        poolclass=NullPool,
        connect_args={"sslmode": "require"},
    )
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()

# ────────────────────────────────
# 7) Entrypoint
# ────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
