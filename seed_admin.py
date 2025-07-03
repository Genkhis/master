from database import SessionLocal
from models import Role, User
from fastapi_users.password import get_password_hash
from uuid import uuid4

db = SessionLocal()

for name in ("admin", "user"):
    if not db.query(Role).filter_by(name=name).first():
        db.add(Role(id=uuid4(), name=name))
db.commit()

if not db.query(User).filter_by(email="admin@example.com").first():
    admin = User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password=get_password_hash("ChangeMe123!"),
        is_active=True,
        is_superuser=True
    )
    admin.roles.append(db.query(Role).filter_by(name="admin").one())
    db.add(admin)
    db.commit()

print("✅ Seed complete")
