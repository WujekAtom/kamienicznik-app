from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.dependencies import require_admin
from app.crud.apartments import get_apartments
from app.models.user import User
from app.models.utility_rate import UtilityType
from app.crud.utility_rates import get_all_rates, create_rate
from typing import Optional
from app.crud.utility_components import (
    get_all_electricity, get_all_gas,
    create_electricity, create_gas,
    get_electricity_by_id, get_gas_by_id,
    create_electricity_from_previous, create_gas_from_previous
)

from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/admin/rates")
templates = Jinja2Templates(directory="app/templates")

UTILITY_LABELS = {
    UtilityType.water: ("Woda", "m\u00b3"),
    UtilityType.electricity: ("Pr\u0105d", "kWh"),
    UtilityType.gas: ("Gaz", "m\u00b3"),
    UtilityType.trash: ("\u015amieci", "os./mies."),
    UtilityType.heating: ("Ogrzewanie", "GJ"),
    UtilityType.community_fee: ("Opłata do wspólnoty", "zł/mies.")
}

@router.get("", response_class=HTMLResponse)
async def list_rates(request: Request, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_admin)):
    rates = await get_all_rates(db)
    electricity_list = await get_all_electricity(db)
    gas_list = await get_all_gas(db)
    apartments = await get_apartments(db)
    return templates.TemplateResponse("admin/rates/list.html", {
        "request": request, "current_user": current_user,
        "rates": rates, "UtilityType": UtilityType, "LABELS": UTILITY_LABELS,
        "electricity_list": electricity_list, "gas_list": gas_list,
        "apartments": apartments,
        "today": date.today(),
    })

@router.post("/new")
async def create_rate_submit(request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    utility_type: str = Form(...), rate_per_unit: Decimal = Form(...),
    unit_label: str = Form(...), valid_from: date = Form(...),
    notes: str = Form(""),
    apartment_id: str=Form(""),):
    apt_id: Optional[int] = int(apartment_id) if apartment_id else None
    await create_rate(db, {
        "apartment_id": apt_id,
        "utility_type": utility_type, "rate_per_unit": rate_per_unit,
        "unit_label": unit_label, "valid_from": valid_from,
        "notes": notes or None,
    })
    return RedirectResponse(url="/admin/rates", status_code=302)

@router.post("/electricity/new")
async def create_electricity_submit(request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    apartment_id: str=Form(""),
    valid_from: date = Form(...), notes: str = Form(""),
    var_rate: Decimal = Form(...),
    extra_trade_cycle: Decimal = Form(...),
    fixed_price: Decimal = Form(...),
    dist_fixed: Decimal = Form(...),
    transition_fee: Decimal = Form(...),
    abonament: Decimal = Form(...),
    power_fee: Decimal = Form(...),
    quality_rate: Decimal = Form(...),
    dist_variable: Decimal = Form(...),
    oze_rate: Decimal = Form(...),
    cogen_rate: Decimal = Form(...)):
    apt_id: Optional[int] = int(apartment_id) if apartment_id else None
    await create_electricity(db, {
        "valid_from": valid_from, "notes": notes or None,
        "var_rate": var_rate, "extra_trade_cycle": extra_trade_cycle,
        "fixed_price": fixed_price, "dist_fixed": dist_fixed,
        "transition_fee": transition_fee, "abonament": abonament,
        "power_fee": power_fee, "quality_rate": quality_rate,
        "dist_variable": dist_variable, "oze_rate": oze_rate,
        "cogen_rate": cogen_rate,
        "apartment_id": apt_id,
    })
    await db.commit()
    return RedirectResponse(url="/admin/rates#electricity", status_code=302)

@router.post("/gas/new")
async def create_gas_submit(request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    apartment_id: str = Form(""),
    valid_from: date = Form(...), notes: str = Form(""),
    abonament: Decimal = Form(...),
    conv_factor: Decimal = Form(...),
    gas_price_per_kwh: Decimal = Form(...),
    vat_pct: Decimal = Form(...),
    dist_fixed: Decimal = Form(...),
    dist_variable: Decimal = Form(...)):
    apt_id: Optional[int] = int(apartment_id) if apartment_id else None
    await create_gas(db, {
        "apartment_id": apt_id,
        "valid_from": valid_from, "notes": notes or None,
        "abonament": abonament, "conv_factor": conv_factor,
        "gas_price_per_kwh": gas_price_per_kwh, "vat_pct": vat_pct,
        "dist_fixed": dist_fixed, "dist_variable": dist_variable,
    })
    await db.commit()
    return RedirectResponse(url="/admin/rates#gas", status_code=302)


@router.get("/electricity/{comp_id}/edit", response_class=HTMLResponse)
async def edit_electricity_form(
    comp_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    comp = await get_electricity_by_id(db, comp_id)
    if not comp:
        return RedirectResponse(url="/admin/rates#electricity", status_code=302)
    apartments = await get_apartments(db)
    return templates.TemplateResponse("admin/rates/electricity_edit.html", {
        "request": request,
        "current_user": current_user,
        "comp": comp,
        "apartments": apartments,
        "today": date.today(),
    })

@router.post("/electricity/{comp_id}/edit")
async def edit_electricity_submit(comp_id: int, request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    apartment_id: str = Form(""),
    valid_from: date = Form(...), notes: str = Form(""),
    var_rate: Decimal = Form(...),
    extra_trade_cycle: Decimal = Form(...),
    fixed_price: Decimal = Form(...),
    dist_fixed: Decimal = Form(...),
    transition_fee: Decimal = Form(...),
    abonament: Decimal = Form(...),
    power_fee: Decimal = Form(...),
    quality_rate: Decimal = Form(...),
    dist_variable: Decimal = Form(...),
    oze_rate: Decimal = Form(...),
    cogen_rate: Decimal = Form(...)):

    prev = await get_electricity_by_id(db, comp_id)
    if not prev:
        return RedirectResponse(url="/admin/rates#electricity", status_code=302)

    apt_id: Optional[int] = int(apartment_id) if apartment_id else None

    await create_electricity_from_previous(db, prev, valid_from=valid_from, overrides={
        "notes": notes or None,
        "apartment_id": apt_id,
        "var_rate": var_rate,
        "extra_trade_cycle": extra_trade_cycle,
        "fixed_price": fixed_price,
        "dist_fixed": dist_fixed,
        "transition_fee": transition_fee,
        "abonament": abonament,
        "power_fee": power_fee,
        "quality_rate": quality_rate,
        "dist_variable": dist_variable,
        "oze_rate": oze_rate,
        "cogen_rate": cogen_rate,
    })
    await db.commit()
    return RedirectResponse(url="/admin/rates#electricity", status_code=302)


@router.get("/gas/{comp_id}/edit", response_class=HTMLResponse)
async def edit_gas_form(
    comp_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    comp = await get_gas_by_id(db, comp_id)
    if not comp:
        return RedirectResponse(url="/admin/rates#gas", status_code=302)
    apartments = await get_apartments(db)
    return templates.TemplateResponse("admin/rates/gas_edit.html", {
        "request": request,
        "current_user": current_user,
        "comp": comp,
        "apartments": apartments,
        "today": date.today(),
    })


@router.post("/gas/{comp_id}/edit")
async def edit_gas_submit(comp_id: int, request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    apartment_id: str = Form(""),
    valid_from: date = Form(...), notes: str = Form(""),
    abonament: Decimal = Form(...),
    conv_factor: Decimal = Form(...),
    gas_price_per_kwh: Decimal = Form(...),
    vat_pct: Decimal = Form(...),
    dist_fixed: Decimal = Form(...),
    dist_variable: Decimal = Form(...)):

    prev = await get_gas_by_id(db, comp_id)
    if not prev:
        return RedirectResponse(url="/admin/rates#gas", status_code=302)

    apt_id: Optional[int] = int(apartment_id) if apartment_id else None

    await create_gas_from_previous(db, prev, valid_from=valid_from, overrides={
        "notes": notes or None,
        "apartment_id": apt_id,
        "abonament": abonament,
        "conv_factor": conv_factor,
        "gas_price_per_kwh": gas_price_per_kwh,
        "vat_pct": vat_pct,
        "dist_fixed": dist_fixed,
        "dist_variable": dist_variable,
    })
    await db.commit()
    return RedirectResponse(url="/admin/rates#gas", status_code=302)
