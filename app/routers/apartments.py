from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.user import User
from app.models.tenant import ContractType, Tenant
from app.crud.apartments import get_apartments, get_apartment, create_apartment, update_apartment
from app.crud.tenants import create_tenant, update_tenant, get_active_tenant_for_apartment
from app.crud.users import create_tenant_user, regenerate_magic_link
from app.crud.meter_readings import get_readings_for_apartment
from app.crud.billing_crud import get_billing_periods_for_apartment
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/admin/apartments")
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def list_apartments(request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_admin)):
    apartments = await get_apartments(db, include_inactive=True)
    return templates.TemplateResponse("admin/apartments/list.html", {
        "request": request, "current_user": current_user, "apartments": apartments
    })

@router.get("/new", response_class=HTMLResponse)
async def new_apartment_form(request: Request, current_user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/apartments/form.html", {
        "request": request, "current_user": current_user, "apartment": None, "error": None
    })

@router.post("/new")
async def create_apartment_submit(request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    address: str = Form(...), description: str = Form(""),
    has_water: bool = Form(False), has_electricity: bool = Form(False),
    has_gas: bool = Form(False), has_trash: bool = Form(False),
    has_heating: bool = Form(False)):
    apt = await create_apartment(db, {
        "address": address, "description": description,
        "has_water": has_water, "has_electricity": has_electricity,
        "has_gas": has_gas, "has_trash": has_trash, "has_heating": has_heating
    })
    return RedirectResponse(url=f"/admin/apartments/{apt.id}", status_code=302)

@router.get("/{apt_id}", response_class=HTMLResponse)
async def apartment_detail(apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(require_admin)):
    apt = await get_apartment(db, apt_id)
    if not apt:
        raise HTTPException(404, "Lokal nie znaleziony")
    tenant = await get_active_tenant_for_apartment(db, apt_id)
    readings = await get_readings_for_apartment(db, apt_id, limit=20)
    billing = await get_billing_periods_for_apartment(db, apt_id)
    magic_link = None
    if tenant and tenant.user:
        magic_link = f"/magic/{tenant.user.magic_link_token}"
    return templates.TemplateResponse("admin/apartments/detail.html", {
        "request": request, "current_user": current_user,
        "apartment": apt, "tenant": tenant,
        "readings": readings, "billing_periods": billing,
        "magic_link": magic_link, "today": date.today(),
        "ContractType": ContractType,
    })

@router.get("/{apt_id}/edit", response_class=HTMLResponse)
async def edit_apartment_form(apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(require_admin)):
    apt = await get_apartment(db, apt_id)
    if not apt:
        raise HTTPException(404)
    return templates.TemplateResponse("admin/apartments/form.html", {
        "request": request, "current_user": current_user, "apartment": apt, "error": None
    })

@router.post("/{apt_id}/edit")
async def update_apartment_submit(apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    address: str = Form(...), description: str = Form(""),
    has_water: bool = Form(False), has_electricity: bool = Form(False),
    has_gas: bool = Form(False), has_trash: bool = Form(False),
    has_heating: bool = Form(False), is_active: bool = Form(False)):
    apt = await get_apartment(db, apt_id)
    if not apt:
        raise HTTPException(404)
    await update_apartment(db, apt, {
        "address": address, "description": description,
        "has_water": has_water, "has_electricity": has_electricity,
        "has_gas": has_gas, "has_trash": has_trash,
        "has_heating": has_heating, "is_active": is_active
    })
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)

@router.post("/{apt_id}/tenant/new")
async def add_tenant(apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    full_name: str = Form(...), email: str = Form(""), phone: str = Form(""),
    contract_start: date = Form(...), contract_end: date = Form(None),
    contract_type: str = Form("indefinite"), rent_amount: Decimal = Form(...),
    payment_due_day: int = Form(10), occupants: int = Form(1), water_advance: Decimal = Form(0), notes: str = Form("")):
    # Deactivate previous tenant
    old_tenant = await get_active_tenant_for_apartment(db, apt_id)
    if old_tenant:
        old_tenant.is_active = False
    tenant = await create_tenant(db, {
        "apartment_id": apt_id, "full_name": full_name,
        "email": email or None, "phone": phone or None,
        "contract_start": contract_start, "contract_end": contract_end,
        "contract_type": contract_type, "rent_amount": rent_amount,
        "payment_due_day": payment_due_day, "occupants": occupants,
        "water_advance": water_advance,
        "notes": notes or None,
    })
    if email:
        user = await create_tenant_user(db, email, tenant.id)
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)

@router.post("/{apt_id}/magic-link/regenerate")
async def regen_magic_link(apt_id: int, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(require_admin)):
    tenant = await get_active_tenant_for_apartment(db, apt_id)
    if tenant and tenant.user:
        await regenerate_magic_link(db, tenant.user)
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)


@router.post("/{apt_id}/tenant/edit")
async def edit_tenant(apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    full_name: str = Form(...), email: str = Form(""), phone: str = Form(""),
    contract_start: date = Form(...), contract_end: date = Form(None),
    contract_type: str = Form("indefinite"), rent_amount: Decimal = Form(...),
    payment_due_day: int = Form(10), occupants: int = Form(1), water_advance: Decimal = Form(0), notes: str = Form("")):
    tenant = await get_active_tenant_for_apartment(db, apt_id)
    if not tenant:
        raise HTTPException(404, "Brak aktywnego najemcy")
    await update_tenant(db, tenant, {
        "full_name": full_name,
        "email": email or None,
        "phone": phone or None,
        "contract_start": contract_start,
        "contract_end": contract_end,
        "contract_type": contract_type,
        "rent_amount": rent_amount,
        "payment_due_day": payment_due_day,
        "occupants": occupants,
        "water_advance": water_advance,
        "notes": notes or None,
    })

    # Update related user account
    get_user_query = select(User).where(User.tenant_id == tenant.id)
    result = await db.execute(get_user_query)
    user_account = result.scalars().first()

    if user_account and email:
        user_account.email = email

    await db.flush()
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)


@router.post("/{apt_id}/tenant/deactivate")
async def deactivate_tenant(apt_id: int, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(require_admin)):
    tenant = await get_active_tenant_for_apartment(db, apt_id)
    if tenant:
        tenant.is_active = False
        await db.flush()
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)
