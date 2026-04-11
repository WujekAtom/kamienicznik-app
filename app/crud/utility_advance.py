from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.utility_advance import UtilityAdvance

async def get_utility_advances_for_apartment(
    db: AsyncSession, apartment_id: int
) -> list[UtilityAdvance]:
    result = await db.execute(
        select(UtilityAdvance).where(
            UtilityAdvance.apartment_id == apartment_id
        )
    )
    return result.scalars().all()