from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
                               get_billing_periods_for_apartment)
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
    tenant = await get_active_tenant_for_apartment(db, apt_id)
    rent = tenant.rent_amount if tenant else Decimal("0")

    bp = await create_billing_period(db, apt_id, period_start, period_end, rent, due_date, notes or None)

    # Czynsz
    await add_billing_item(db, bp.id, "rent", "Czynsz podstawowy", rent)

    # Media
    all_readings = await get_readings_for_apartment(db, apt_id, limit=200)

    def get_readings(ut):
        in_p = [r for r in all_readings if r.utility_type == ut and period_start <= r.reading_date <= period_end]
        bef_p = [r for r in all_readings if r.utility_type == ut and r.reading_date < period_start]
        if not in_p or not bef_p:
            return None, None, None
        r_to = max(in_p, key=lambda r: r.reading_date)
        r_from = max(bef_p, key=lambda r: r.reading_date)
        cons = r_to.reading_value - r_from.reading_value
        if cons <= 0:
            return None, None, None
        return r_from, r_to, cons

    # --- WODA ---
    if apt.has_water:
        water_rate = await get_current_rate(db, UtilityType.water, period_end, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.water)
        if water_rate and cons is not None:
            usage_cost = (cons * water_rate.rate_per_unit).quantize(Decimal("0.01"))
            adv = (tenant.water_advance.quantize(Decimal("0.01"))
                   if tenant and tenant.water_advance and tenant.water_advance > 0
                   else Decimal("0.00"))
            net_water = (usage_cost - adv).quantize(Decimal("0.01"))
            if adv > 0:
                desc = (f"Woda: {float(cons):.3f} m³ × {float(water_rate.rate_per_unit):.4f} zł/m³"
                        f" = {float(usage_cost):.2f} zł − zaliczka {float(adv):.2f} zł"
                        f" = {float(net_water):.2f} zł")
            else:
                desc = f"Woda: {float(cons):.3f} m³ × {float(water_rate.rate_per_unit):.4f} zł/m³"
            await add_billing_item(db, bp.id, "water", desc, net_water,
                                   quantity=cons, unit_price=water_rate.rate_per_unit,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)

    # --- PRĄD (składowe z faktury) ---
    if apt.has_electricity:
        elec = await get_current_electricity(db, period_end, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.electricity)
        if elec and cons is not None:
            kwh = cons
            # Sprzedaż energii
            var_total = (kwh * elec.var_rate).quantize(Decimal("0.01"))
            fixed_sale = (elec.extra_trade_cycle + elec.fixed_price).quantize(Decimal("0.01"))
            sale_total = (var_total + fixed_sale).quantize(Decimal("0.01"))
            # Dystrybucja
            dist_var = (kwh * (elec.quality_rate + elec.dist_variable + elec.oze_rate + elec.cogen_rate)).quantize(Decimal("0.01"))
            dist_fixed = (elec.dist_fixed + elec.transition_fee + elec.abonament + elec.power_fee).quantize(Decimal("0.01"))
            dist_total = (dist_var + dist_fixed).quantize(Decimal("0.01"))
            elec_total = (sale_total + dist_total).quantize(Decimal("0.01"))
            vat = (elec_total * 23 / Decimal("100")).quantize(Decimal("0.01"))
            elec_total_vat = (elec_total + vat).quantize(Decimal("0.01"))
            desc = (f"Prąd: {float(kwh):.3f} kWh | "
                    f"sprzedaż: {float(sale_total):.2f} zł, dystr.: {float(dist_total):.2f} zł + VAT 23%: {float(vat):.2f} zł")
            await add_billing_item(db, bp.id, "electricity", desc, elec_total_vat,
                                   quantity=kwh, unit_price=None,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)

    # --- GAZ (składowe z faktury) ---
    if apt.has_gas:
        gas = await get_current_gas(db, period_end, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.gas)
        if gas and cons is not None:
            m3 = cons
            kwh_gas = (m3 * gas.conv_factor).quantize(Decimal("0.000001"))
            fuel_netto = (kwh_gas * gas.gas_price_per_kwh).quantize(Decimal("0.01"))
            dist_var = (kwh_gas * gas.dist_variable).quantize(Decimal("0.01"))
            netto = (fuel_netto + gas.dist_fixed + gas.abonament + dist_var).quantize(Decimal("0.01"))
            vat = (netto * gas.vat_pct / Decimal("100")).quantize(Decimal("0.01"))
            gas_total = (netto + vat).quantize(Decimal("0.01"))
            desc = (f"Gaz: {float(m3):.3f} m³ → {float(kwh_gas):.1f} kWh | "
                    f"netto: {float(netto):.2f} zł + VAT {float(gas.vat_pct):.0f}%: {float(vat):.2f} zł")
            await add_billing_item(db, bp.id, "gas", desc, gas_total,
                                   quantity=m3, unit_price=None,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)

    # --- OGRZEWANIE (prosta stawka) ---
    if apt.has_heating:
        heat_rate = await get_current_rate(db, UtilityType.heating, period_end, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.heating)
        if heat_rate and cons is not None:
            total = (cons * heat_rate.rate_per_unit).quantize(Decimal("0.01"))
            desc = f"Ogrzewanie: {float(cons):.3f} GJ × {float(heat_rate.rate_per_unit):.4f} zł/GJ"
            await add_billing_item(db, bp.id, "heating", desc, total,
                                   quantity=cons, unit_price=heat_rate.rate_per_unit,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)

    # --- ŚMIECI (stawka × liczba osób) ---
    if apt.has_trash and tenant:
        trash_rate = await get_current_rate(db, UtilityType.trash, period_end, apartment_id=apt.id)
        if trash_rate:
            occupants = tenant.occupants or 1
            trash_total = (Decimal(str(occupants)) * trash_rate.rate_per_unit).quantize(Decimal("0.01"))
            desc = f"Śmieci: {occupants} os. × {float(trash_rate.rate_per_unit):.2f} zł/os."
            await add_billing_item(db, bp.id, "trash", desc, trash_total,
                                   quantity=Decimal(str(occupants)),
                                   unit_price=trash_rate.rate_per_unit)

    # --- CZYNSZ DO WSPÓLNOTY ( zł / miesiąc) ---

    community_rate = await get_current_rate(db, UtilityType.community_fee, period_end, apartment_id=apt.id)
    if community_rate:
        total = community_rate.rate_per_unit.quantize(Decimal("0.01"))
        desc = f"Czynsz do wspólnoty: {float(community_rate.rate_per_unit):.2f} zł/mies."
        await add_billing_item(db, bp.id, "community_fee", desc, total, quantity=Decimal("1.00"), unit_price=community_rate.rate_per_unit)

    await recalculate_billing_totals(db, bp)
    await db.commit()
    return RedirectResponse(url=f"/admin/billing/{bp.id}", status_code=302)


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
        await db.commit()
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
    await db.commit()
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
    await db.commit()
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
    await db.commit()
    return RedirectResponse(url=f"/admin/billing/{bp_id}", status_code=302)


@router.post("/{bp_id}/revert-to-draft")
async def revert_to_draft(bp_id: int, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_admin)):
    result = await db.execute(select(BillingPeriod).where(BillingPeriod.id == bp_id))
    bp = result.scalar_one_or_none()
    if bp and bp.status != BillingStatus.paid:
        bp.status = BillingStatus.draft
        await db.commit()
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
    await db.commit()
    target = redirect_to if redirect_to else f"/admin/apartments/{apt_id}"
    return RedirectResponse(url=target, status_code=302)
