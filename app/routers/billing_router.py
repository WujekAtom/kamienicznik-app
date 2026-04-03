from typing import List

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.user import User
from app.models.apartment import Apartment
from app.models.billing import BillingPeriod, BillingStatus
from app.models.billing import BillingItem
from app.models.payment import Payment, PaymentType
from app.crud.apartments import get_apartment
from app.crud.billing import (create_billing_period, get_billing_period,
                               add_billing_item, recalculate_billing_totals,
                               get_billing_periods_for_apartment, create_billing_for_apartment_and_period)
from app.crud.payments import add_payment
from app.crud.tenants import get_active_tenant_for_apartment
from app.crud.utility_rates import get_current_rate
from app.crud.utility_components import get_current_electricity, get_current_gas
from app.crud.meter_readings import get_last_reading, get_readings_for_apartment
from app.models.utility_rate import UtilityType
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/admin/billing")
templates = Jinja2Templates(directory="app/templates")

UTILITY_MAP = {
    "water":       (UtilityType.water,       "Woda"),
    "electricity": (UtilityType.electricity, "Prąd"),
    "gas":         (UtilityType.gas,         "Gaz"),
    "heating":     (UtilityType.heating,     "Ogrzewanie"),
    "community_fee": (UtilityType.community_fee, "Czynsz do wspólnoty")
}


@router.get("/list", response_class=HTMLResponse)
async def all_billing(request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(require_admin)):
    result = await db.execute(
        select(BillingPeriod)
        .options(selectinload(BillingPeriod.apartment))
        .order_by(BillingPeriod.period_start.desc())
        .limit(100)
    )
    periods = result.scalars().all()
    return templates.TemplateResponse("admin/billing/list.html", {
        "request": request, "current_user": current_user,
        "periods": periods, "BillingStatus": BillingStatus, "today": date.today()
    })


@router.get("/new/{apt_id}", response_class=HTMLResponse)
async def new_billing_form(apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(require_admin)):
    apt = await get_apartment(db, apt_id)
    if not apt:
        raise HTTPException(404)
    tenant = await get_active_tenant_for_apartment(db, apt_id)
    return templates.TemplateResponse("admin/billing/new.html", {
        "request": request, "current_user": current_user,
        "apartment": apt, "tenant": tenant, "today": date.today(),
    })


@router.post("/new/{apt_id}")
async def create_billing_submit(
        apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin),
        period_start: date = Form(...), period_end: date = Form(...),
        due_date: date = Form(...), notes: str = Form("")):

    apt = await get_apartment(db, apt_id)
    if not apt:
        raise HTTPException(404)

    bp, missing = await create_billing_for_apartment_and_period(db, apt_id, period_start, period_end, due_date, notes )

    return RedirectResponse(url=f"/admin/billing/{bp.id}", status_code=302)

@router.post("/bulk")
async def create_billing_bulk(request: Request,
    apartment_ids: List[int] = Form(...),
    period_from: date = Form(...),
    period_to: date = Form(...),
    due_to: date = Form(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),):

    results = []

    for apt_id in apartment_ids:
        billing, missing = await create_billing_for_apartment_and_period(
            db=db,
            apartment_id=apt_id,
            period_from=period_from,
            period_to=period_to,
            due_to=due_to,
            notes="Wygenerowane zbiorowo"
        )

        apt = await get_apartment(db, apt_id)  # żeby mieć adres

        if billing:
            results.append({
                "apartment_id": apt_id,
                "address": apt.address,  # albo zlepka ulicy/numeru
                "status": "ok",
                "message": "",
                "amount": float(billing.total_amount),  # lub inna kolumna
                "billing_id": billing.id,
            })
        elif missing:
            results.append({
                "apartment_id": apt_id,
                "address": apt.address if apt else f"Lokal {apt_id}",
                "status": "no_readings",
                "message": f"Brak odczytów: {', '.join(missing)}",
                "amount": None,
                "billing_id": None,
            })
        else:
            results.append({
                "apartment_id": apt_id,
                "address": apt.address if apt else f"Lokal {apt_id}",
                "status": "error",
                "message": "Nie udało się utworzyć rozliczenia",
                "amount": None,
                "billing_id": None,
            })

    return templates.TemplateResponse(
        "bulk_billing_result.html",
        {
            "request": request,
            "results": results,
            "period_from": period_from,
            "period_to": period_to,
            "current_user": current_user,
        },
    )


@router.post("/delete-billing-bulk")
async def delete_billing_bulk(request: Request,
    billing_ids: List[int] = Form(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),):

    if not billing_ids:
        return RedirectResponse(url="/admin/billing/list", status_code=302)

    billings_to_delete = delete(BillingPeriod).where(BillingPeriod.id.in_(billing_ids))
    await db.execute(billings_to_delete)

    return RedirectResponse(url="/admin/billing/list", status_code=302)

@router.get("/{bp_id}", response_class=HTMLResponse)
async def billing_detail(bp_id: int, request: Request, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(require_admin)):
    bp = await get_billing_period(db, bp_id)
    if not bp:
        raise HTTPException(404)
    tenant = await get_active_tenant_for_apartment(db, bp.apartment_id)
    return templates.TemplateResponse("admin/billing/detail.html", {
        "request": request, "current_user": current_user,
        "bp": bp, "tenant": tenant,
        "BillingStatus": BillingStatus, "PaymentType": PaymentType,
        "today": date.today(),
    })


@router.post("/{bp_id}/issue")
async def issue_billing(bp_id: int, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(require_admin)):
    result = await db.execute(select(BillingPeriod).where(BillingPeriod.id == bp_id))
    bp = result.scalar_one_or_none()
    if bp and bp.status == BillingStatus.draft:
        bp.status = BillingStatus.issued
        await db.flush()
    return RedirectResponse(url=f"/admin/billing/{bp_id}", status_code=302)


@router.post("/{bp_id}/payment")
async def add_payment_submit(
        bp_id: int, request: Request, db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin),
        payment_date: date = Form(...), amount: Decimal = Form(...),
        payment_type: str = Form(...), cash_amount: str = Form(""),
        transfer_amount: str = Form(""), reference_number: str = Form(""),
        notes: str = Form("")):
    bp = await get_billing_period(db, bp_id)
    if not bp:
        raise HTTPException(404)
    cash = Decimal(cash_amount) if cash_amount.strip() else None
    transfer = Decimal(transfer_amount) if transfer_amount.strip() else None
    await add_payment(
        db, bp_id, payment_date, amount, PaymentType(payment_type),
        cash, transfer,
        reference_number or None, notes or None, current_user.id
    )
    await recalculate_billing_totals(db, bp)
    await db.flush()
    return RedirectResponse(url=f"/admin/billing/{bp_id}", status_code=302)


@router.post("/{bp_id}/item/{item_id}/delete")
async def delete_billing_item(bp_id: int, item_id: int, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(require_admin)):
    from app.models.billing import BillingItem
    result = await db.execute(select(BillingItem).where(BillingItem.id == item_id,
                                                         BillingItem.billing_period_id == bp_id))
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
    bp = await get_billing_period(db, bp_id)
    if bp:
        await recalculate_billing_totals(db, bp)
    await db.flush()
    return RedirectResponse(url=f"/admin/billing/{bp_id}", status_code=302)


@router.post("/{bp_id}/edit")
async def edit_billing_period(bp_id: int, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    due_date: date = Form(...), notes: str = Form("")):
    result = await db.execute(select(BillingPeriod).where(BillingPeriod.id == bp_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(404)
    bp.due_date = due_date
    bp.notes = notes or None
    await db.flush()
    return RedirectResponse(url=f"/admin/billing/{bp_id}", status_code=302)


@router.post("/{bp_id}/revert-to-draft")
async def revert_to_draft(bp_id: int, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_admin)):
    result = await db.execute(select(BillingPeriod).where(BillingPeriod.id == bp_id))
    bp = result.scalar_one_or_none()
    if bp and bp.status != BillingStatus.paid:
        bp.status = BillingStatus.draft
        await db.flush()
    return RedirectResponse(url=f"/admin/billing/{bp_id}", status_code=302)


@router.post("/{bp_id}/delete")
async def delete_billing_period(bp_id: int, db: AsyncSession = Depends(get_db),
                                 current_user: User = Depends(require_admin), redirect_to: str=Form("")):
    result = await db.execute(select(BillingPeriod).where(BillingPeriod.id == bp_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(404)
    apt_id = bp.apartment_id
    await db.delete(bp)
    await db.flush()
    target = redirect_to if redirect_to else f"/admin/apartments/{apt_id}"
    return RedirectResponse(url=target, status_code=302)
