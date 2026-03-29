from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.utility_components import ElectricityComponents, GasComponents
from datetime import date


async def get_current_electricity(
    db: AsyncSession,
    on_date: date = None,
    apartment_id: int = None,
) -> ElectricityComponents | None:
    if on_date is None:
        on_date = date.today()

    base_filter = [
        ElectricityComponents.valid_from <= on_date,
        (ElectricityComponents.valid_to == None) | (ElectricityComponents.valid_to >= on_date),
    ]

    if apartment_id is not None:
        result = await db.execute(
            select(ElectricityComponents)
            .where(*base_filter, ElectricityComponents.apartment_id == apartment_id)
            .order_by(ElectricityComponents.valid_from.desc()).limit(1)
        )
        comp = result.scalar_one_or_none()
        if comp:
            return comp

    result = await db.execute(
        select(ElectricityComponents)
        .where(*base_filter, ElectricityComponents.apartment_id == None)
        .order_by(ElectricityComponents.valid_from.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def get_current_gas(
    db: AsyncSession,
    on_date: date = None,
    apartment_id: int = None,
) -> GasComponents | None:
    if on_date is None:
        on_date = date.today()

    base_filter = [
        GasComponents.valid_from <= on_date,
        (GasComponents.valid_to == None) | (GasComponents.valid_to >= on_date),
    ]

    if apartment_id is not None:
        result = await db.execute(
            select(GasComponents)
            .where(*base_filter, GasComponents.apartment_id == apartment_id)
            .order_by(GasComponents.valid_from.desc()).limit(1)
        )
        comp = result.scalar_one_or_none()
        if comp:
            return comp

    result = await db.execute(
        select(GasComponents)
        .where(*base_filter, GasComponents.apartment_id == None)
        .order_by(GasComponents.valid_from.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def get_all_electricity(db: AsyncSession):
    result = await db.execute(
        select(ElectricityComponents).order_by(ElectricityComponents.valid_from.desc())
    )
    return result.scalars().all()


async def get_all_gas(db: AsyncSession):
    result = await db.execute(
        select(GasComponents).order_by(GasComponents.valid_from.desc())
    )
    return result.scalars().all()


async def create_electricity(db: AsyncSession, data: dict) -> ElectricityComponents:
    prev = await get_current_electricity(db)
    if prev and prev.valid_to is None:
        prev.valid_to = data["valid_from"]
    obj = ElectricityComponents(**data)
    db.add(obj)
    await db.flush()
    return obj


async def create_gas(db: AsyncSession, data: dict) -> GasComponents:
    prev = await get_current_gas(db)
    if prev and prev.valid_to is None:
        prev.valid_to = data["valid_from"]
    obj = GasComponents(**data)
    db.add(obj)
    await db.flush()
    return obj
    
    

async def get_electricity_by_id(db: AsyncSession, comp_id: int) -> ElectricityComponents | None:
    result = await db.execute(select(ElectricityComponents).where(ElectricityComponents.id == comp_id))
    return result.scalar_one_or_none()


async def get_gas_by_id(db: AsyncSession, comp_id: int) -> GasComponents | None:
    result = await db.execute(select(GasComponents).where(GasComponents.id == comp_id))
    return result.scalar_one_or_none()


def _electricity_to_dict(e: ElectricityComponents) -> dict:
    return {
        "valid_from": e.valid_from,
        "notes": e.notes,
        "var_rate": e.var_rate,
        "extra_trade_cycle": e.extra_trade_cycle,
        "fixed_price": e.fixed_price,
        "dist_fixed": e.dist_fixed,
        "transition_fee": e.transition_fee,
        "abonament": e.abonament,
        "power_fee": e.power_fee,
        "quality_rate": e.quality_rate,
        "dist_variable": e.dist_variable,
        "oze_rate": e.oze_rate,
        "cogen_rate": e.cogen_rate,
    }


def _gas_to_dict(g: GasComponents) -> dict:
    return {
        "valid_from": g.valid_from,
        "notes": g.notes,
        "abonament": g.abonament,
        "conv_factor": g.conv_factor,
        "gas_price_per_kwh": g.gas_price_per_kwh,
        "vat_pct": g.vat_pct,
        "dist_fixed": g.dist_fixed,
        "dist_variable": g.dist_variable,
    }


async def create_electricity_from_previous(db: AsyncSession, previous: ElectricityComponents, *, valid_from: date, overrides: dict) -> ElectricityComponents:
    data = _electricity_to_dict(previous)
    data.update(overrides)
    data["valid_from"] = valid_from
    if previous.valid_to is None:
        previous.valid_to = valid_from
    obj = ElectricityComponents(**data)
    db.add(obj)
    await db.flush()
    return obj


async def create_gas_from_previous(db: AsyncSession, previous: GasComponents, *, valid_from: date, overrides: dict) -> GasComponents:
    data = _gas_to_dict(previous)
    data.update(overrides)
    data["valid_from"] = valid_from
    if previous.valid_to is None:
        previous.valid_to = valid_from
    obj = GasComponents(**data)
    db.add(obj)
    await db.flush()
    return obj
