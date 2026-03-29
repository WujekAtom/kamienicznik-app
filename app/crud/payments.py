from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.payment import Payment, PaymentType
from app.models.billing import BillingPeriod
from decimal import Decimal
from datetime import date

async def add_payment(db: AsyncSession, bp_id: int, payment_date: date,
                      amount: Decimal, payment_type: PaymentType,
                      cash_amount: Decimal = None, transfer_amount: Decimal = None,
                      reference_number: str = None, notes: str = None,
                      registered_by_id: int = None) -> Payment:
    payment = Payment(
        billing_period_id=bp_id,
        payment_date=payment_date,
        amount=amount,
        payment_type=payment_type,
        cash_amount=cash_amount,
        transfer_amount=transfer_amount,
        reference_number=reference_number,
        notes=notes,
        registered_by_id=registered_by_id,
    )
    db.add(payment)
    await db.flush()
    return payment

async def get_recent_payments(db: AsyncSession, limit: int = 20):
    result = await db.execute(
        select(Payment)
        .options(
            selectinload(Payment.billing_period).selectinload(BillingPeriod.apartment),
            selectinload(Payment.registered_by)
        )
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
        .limit(limit)
    )
    return result.scalars().all()
