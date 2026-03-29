from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.meter_reading import MeterReading
from app.models.utility_rate import UtilityType
from decimal import Decimal

async def get_last_reading(db: AsyncSession, apt_id: int, utility_type: UtilityType) -> MeterReading | None:
    result = await db.execute(
        select(MeterReading)
        .where(MeterReading.apartment_id == apt_id, MeterReading.utility_type == utility_type)
        .order_by(MeterReading.reading_date.desc(), MeterReading.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

async def get_readings_for_apartment(db: AsyncSession, apt_id: int, limit: int = 50):
    result = await db.execute(
        select(MeterReading)
        .where(MeterReading.apartment_id == apt_id)
        .options(selectinload(MeterReading.submitted_by))
        .order_by(MeterReading.reading_date.desc(), MeterReading.id.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def create_reading(db: AsyncSession, apt_id: int, utility_type: UtilityType,
                         reading_date, reading_value: Decimal,
                         submitted_by_id: int = None, notes: str = None,
                         photo_path: str = None) -> MeterReading:
    prev = await get_last_reading(db, apt_id, utility_type)
    consumption = None
    prev_id = None
    if prev:
        consumption = reading_value - prev.reading_value
        prev_id = prev.id
    reading = MeterReading(
        apartment_id=apt_id,
        utility_type=utility_type,
        reading_date=reading_date,
        reading_value=reading_value,
        consumption=consumption,
        previous_reading_id=prev_id,
        submitted_by_id=submitted_by_id,
        notes=notes,
        photo_path=photo_path,
    )
    db.add(reading)
    await db.flush()
    return reading
