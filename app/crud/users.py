from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.auth.security import hash_password, generate_magic_token
from app.config import get_settings
from datetime import datetime, timedelta, timezone

settings = get_settings()

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_magic_token(db: AsyncSession, token: str) -> User | None:
    result = await db.execute(
        select(User).where(
            User.magic_link_token == token,
            User.magic_link_expires > datetime.now(timezone.utc),
            User.is_active == True
        ).options(selectinload(User.tenant).selectinload(Tenant.apartment))
    )
    return result.scalar_one_or_none()

async def create_admin_user(db: AsyncSession, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password), role=UserRole.admin)
    db.add(user)
    await db.flush()
    return user

async def create_tenant_user(db: AsyncSession, email: str, tenant_id: int) -> User:
    token = generate_magic_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.magic_link_expire_days * 365)
    user = User(
        email=email,
        role=UserRole.tenant,
        tenant_id=tenant_id,
        magic_link_token=token,
        magic_link_expires=expires,
    )
    db.add(user)
    await db.flush()
    return user

async def regenerate_magic_link(db: AsyncSession, user: User) -> str:
    token = generate_magic_token()
    user.magic_link_token = token
    user.magic_link_expires = datetime.now(timezone.utc) + timedelta(days=settings.magic_link_expire_days * 365)
    await db.flush()
    return token

async def get_user_by_reset_token(db: AsyncSession, token: str) -> User | None:
    result = await db.execute(select(User).where(User.reset_token == token))
    return result.scalar_one_or_none()