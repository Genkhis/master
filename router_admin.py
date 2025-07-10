from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Role
from schemas_user import UserRead, UserCreate, UserUpdate
from hashing import get_password_hash          # your bcrypt helper

admin_router = APIRouter(prefix="/admin/users", tags=["Admin – Users"])

@admin_router.get("/", response_model=list[UserRead])
async def list_users(_, db: AsyncSession = Depends(get_db),
                     __ = Depends(superuser_required)):
    result = await db.execute(select(User).order_by(User.email))
    return result.scalars().all()

@admin_router.post("/", response_model=UserRead, status_code=201)
async def create_user(payload: UserCreate,
                      __ = Depends(superuser_required),
                      db: AsyncSession = Depends(get_db)):
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_superuser=payload.is_superuser,
    )
    if payload.roles:
        roles = (await db.execute(select(Role).where(Role.id.in_(payload.roles)))
                 ).scalars().all()
        user.roles = roles
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@admin_router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: UUID, payload: UserUpdate,
                      __ = Depends(superuser_required),
                      db: AsyncSession = Depends(get_db)):
    user: User = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    # field-by-field patch
    if payload.email:        user.email = payload.email
    if payload.password:     user.hashed_password = get_password_hash(payload.password)
    if payload.is_active is not None:    user.is_active = payload.is_active
    if payload.is_superuser is not None: user.is_superuser = payload.is_superuser
    if payload.roles is not None:
        roles = (await db.execute(select(Role).where(Role.id.in_(payload.roles)))
                 ).scalars().all()
        user.roles = roles
    await db.commit(); await db.refresh(user)
    return user
