from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.apartment import Apartment
from app.models.tenant import Tenant

async def get_apartments(db: AsyncSession, include_inactive: bool = False):
    q = select(Apartment).options(selectinload(Apartment.tenants))
    if not include_inactive:
        q = q.where(Apartment.is_active == True)
    q = q.order_by(Apartment.address)
    result = await db.execute(q)
    return result.scalars().all()

async def get_apartment(db: AsyncSession, apt_id: int) -> Apartment | None:
    result = await db.execute(
        select(Apartment).where(Apartment.id == apt_id)
        .options(selectinload(Apartment.tenants), selectinload(Apartment.billing_periods))
    )
    return result.scalar_one_or_none()

async def create_apartment(db: AsyncSession, data: dict) -> Apartment:
    apt = Apartment(**data)
    db.add(apt)
    await db.flush()
    return apt

async def update_apartment(db: AsyncSession, apt: Apartment, data: dict) -> Apartment:
    for k, v in data.items():
        setattr(apt, k, v)
    await db.flush()
    return apt
