from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.tenant import Tenant


async def get_tenant(db: AsyncSession, tenant_id: int) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
        .options(selectinload(Tenant.apartment), selectinload(Tenant.user))
    )
    return result.scalar_one_or_none()


async def get_active_tenant_for_apartment(db: AsyncSession, apt_id: int) -> Tenant | None:
    result = await db.execute(
        select(Tenant)
        .where(Tenant.apartment_id == apt_id, Tenant.is_active == True)
        .options(selectinload(Tenant.apartment), selectinload(Tenant.user))
    )
    return result.scalar_one_or_none()


async def create_tenant(db: AsyncSession, data: dict) -> Tenant:
    tenant = Tenant(**data)
    db.add(tenant)
    await db.flush()
    return tenant


async def update_tenant(db: AsyncSession, tenant: Tenant, data: dict) -> Tenant:
    for k, v in data.items():
        setattr(tenant, k, v)
    await db.flush()
    return tenant

