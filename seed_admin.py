"""
Create the default roles ('admin', 'user') and an initial super-user
(admin@example.com / ChangeMe123!).

The script is **idempotent** – running it twice will not create duplicates.
"""

from pathlib import Path
import os

# ──────────────────────────────────────────────────────────────
# 1) Load .env so DATABASE_URL / DATABASE_ADMIN_URL are present
# ──────────────────────────────────────────────────────────────
if Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

# ──────────────────────────────────────────────────────────────
# 2) Local imports – AFTER env vars are available
# ──────────────────────────────────────────────────────────────
from database import SessionLocal
from models    import Role, User
from fastapi_users.password import PasswordHelper   # v12 helper

pwd_helper = PasswordHelper()
db = SessionLocal()

try:
    # ──────────────────────────────────────────────────────────
    # 3) Ensure roles exist
    # ──────────────────────────────────────────────────────────
    for role_name in ("admin", "user"):
        if not db.query(Role).filter_by(name=role_name).first():
            db.add(Role(name=role_name))
    db.commit()

    # ──────────────────────────────────────────────────────────
    # 4) Seed the first super-user
    # ──────────────────────────────────────────────────────────
    admin_email = "admin@example.com"
    raw_pw      = "ChangeMe123!"

    admin = db.query(User).filter_by(email=admin_email).first()

    if not admin:
        admin = User(
            email=admin_email,
            hashed_password=pwd_helper.hash(raw_pw),
            is_active=True,
            is_superuser=True,
        )
        admin_role = db.query(Role).filter_by(name="admin").one()
        admin.roles.append(admin_role)

        db.add(admin)
        db.commit()
        print("✓ Admin user created:", admin_email)
    else:
        print("✓ Admin user already exists:", admin_email)

finally:
    db.close()
