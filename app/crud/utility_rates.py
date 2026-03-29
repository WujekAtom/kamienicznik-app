from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.utility_rate import UtilityRate, UtilityType
from datetime import date

async def get_current_rate(
    db: AsyncSession,
    utility_type: UtilityType,
    on_date: date = None,
    apartment_id: int = None,
) -> UtilityRate | None:
    if on_date is None:
        on_date = date.today()

    base_filter = [
        UtilityRate.utility_type == utility_type,
        UtilityRate.valid_from <= on_date,
        (UtilityRate.valid_to == None) | (UtilityRate.valid_to >= on_date),
    ]

    # Najpierw szukaj stawki dedykowanej dla lokalu
    if apartment_id is not None:
        result = await db.execute(
            select(UtilityRate)
            .where(*base_filter, UtilityRate.apartment_id == apartment_id)
            .order_by(UtilityRate.valid_from.desc())
            .limit(1)
        )
        rate = result.scalar_one_or_none()
        if rate:
            return rate

    # Fallback – stawka globalna (apartment_id IS NULL)
    result = await db.execute(
        select(UtilityRate)
        .where(*base_filter, UtilityRate.apartment_id == None)
        .order_by(UtilityRate.valid_from.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

async def get_all_rates(db: AsyncSession):
    result = await db.execute(
        select(UtilityRate).order_by(UtilityRate.utility_type, UtilityRate.valid_from.desc())
    )
    return result.scalars().all()

async def get_rates_for_apartment(db: AsyncSession, apartment_id: int):
    """Zwraca stawki przypisane do konkretnego lokalu."""
    result = await db.execute(
        select(UtilityRate)
        .where(UtilityRate.apartment_id == apartment_id)
        .order_by(UtilityRate.utility_type, UtilityRate.valid_from.desc())
    )
    return result.scalars().all()


async def create_rate(db: AsyncSession, data: dict) -> UtilityRate:
    apt_id = data.get("apartment_id")
    # Zamknij poprzednią otwartą stawkę tego samego typu dla tego samego lokalu/globalną
    prev = await get_current_rate(
        db, data["utility_type"], apartment_id=apt_id
    )
    if prev and prev.apartment_id == apt_id and prev.valid_to is None:
        prev.valid_to = data["valid_from"]
    rate = UtilityRate(**data)
    db.add(rate)
    await db.flush()
    return rate