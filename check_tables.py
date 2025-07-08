# check_tables.py  – SQLAlchemy 2-style
import os, sqlalchemy as sa
from sqlalchemy import text
from pathlib import Path

if "DATABASE_ADMIN_URL" not in os.environ and Path(".env").exists():
    from dotenv import load_dotenv; load_dotenv(override=True)

dsn = os.environ["DATABASE_ADMIN_URL"]
engine = sa.create_engine(dsn, connect_args={"sslmode": "require"})

with engine.connect() as conn:
    rows = conn.execute(
        text("""
            SELECT tablename
              FROM pg_tables
             WHERE schemaname = 'public'
               AND tablename IN ('users','roles','roles_users')
             ORDER BY tablename
        """)
    ).fetchall()

print("\nExisting auth tables:")
print(" • " + "\n • ".join(r[0] for r in rows) if rows else " (none)")
