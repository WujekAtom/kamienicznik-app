from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.billing import BillingPeriod, BillingItem, BillingStatus
from app.models.payment import Payment
from decimal import Decimal
from datetime import date


async def get_billing_periods_for_apartment(db: AsyncSession, apt_id: int):
    result = await db.execute(
        select(BillingPeriod)
        .where(BillingPeriod.apartment_id == apt_id)
        .options(selectinload(BillingPeriod.items), selectinload(BillingPeriod.payments))
        .order_by(BillingPeriod.period_start.desc())
    )
    return result.scalars().all()


async def get_billing_period(db: AsyncSession, bp_id: int) -> BillingPeriod | None:
    result = await db.execute(
        select(BillingPeriod)
        .where(BillingPeriod.id == bp_id)
        .options(
            selectinload(BillingPeriod.items),
            selectinload(BillingPeriod.payments).selectinload(Payment.registered_by),
            selectinload(BillingPeriod.apartment),
        )
    )
    return result.scalar_one_or_none()


async def create_billing_period(db: AsyncSession, apt_id: int, period_start: date,
                                 period_end: date, rent_amount: Decimal,
                                 due_date: date, notes: str = None) -> BillingPeriod:
    bp = BillingPeriod(
        apartment_id=apt_id,
        period_start=period_start,
        period_end=period_end,
        rent_amount=rent_amount,
        total_utilities=Decimal("0"),
        total_amount=rent_amount,
        amount_paid=Decimal("0"),
        status=BillingStatus.draft,
        due_date=due_date,
        notes=notes,
    )
    db.add(bp)
    await db.flush()
    return bp


async def add_billing_item(db: AsyncSession, bp_id: int, item_type: str, description: str,
                            total_price: Decimal, quantity=None, unit_price=None,
                            reading_from_id=None, reading_to_id=None) -> BillingItem:
    item = BillingItem(
        billing_period_id=bp_id,
        item_type=item_type,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
        reading_from_id=reading_from_id,
        reading_to_id=reading_to_id,
    )
    db.add(item)
    await db.flush()
    return item


async def recalculate_billing_totals(db: AsyncSession, bp: BillingPeriod):
    # Explicitly load items and payments from DB — never rely on lazy load in async
    items_res = await db.execute(
        select(BillingItem).where(BillingItem.billing_period_id == bp.id)
    )
    items = items_res.scalars().all()

    payments_res = await db.execute(
        select(Payment).where(Payment.billing_period_id == bp.id)
    )
    payments = payments_res.scalars().all()

    utility_total = sum(
        item.total_price for item in items if item.item_type != "rent"
    )
    rent_total = sum(
        item.total_price for item in items if item.item_type == "rent"
    )
    bp.total_utilities = utility_total
    bp.rent_amount = rent_total if rent_total > 0 else bp.rent_amount
    bp.total_amount = bp.rent_amount + utility_total
    bp.amount_paid = sum(p.amount for p in payments)

    today = date.today()
    if bp.amount_paid >= bp.total_amount:
        bp.status = BillingStatus.paid
    elif today > bp.due_date and bp.amount_paid < bp.total_amount:
        bp.status = BillingStatus.overdue
    elif bp.status == BillingStatus.draft:
        pass  # keep draft
    await db.flush()
