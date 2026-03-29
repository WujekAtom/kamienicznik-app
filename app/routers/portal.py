from fastapi import APIRouter, Depends, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.utility_rate import UtilityType
from app.crud.apartments import get_apartment
from app.crud.tenants import get_active_tenant_for_apartment
from app.crud.meter_readings import get_readings_for_apartment, get_last_reading, create_reading
from app.crud.billing import get_billing_periods_for_apartment
from app.config import get_settings
from datetime import date
from decimal import Decimal
import os, uuid, aiofiles

router = APIRouter(prefix="/portal")
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()

UTILITY_LABELS = {
    "water": ("💧", "Woda", "m³"),
    "electricity": ("⚡", "Prąd", "kWh"),
    "gas": ("🔥", "Gaz", "m³"),
    #"trash": ("🗑️", "Śmieci", "os."),
    "heating": ("🌡️", "Ogrzewanie", "GJ"),
}

@router.get("", response_class=HTMLResponse)
async def portal_home(request: Request, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.admin:
        return RedirectResponse(url="/admin", status_code=302)
    if not current_user.tenant_id:
        return templates.TemplateResponse("tenant/no_apartment.html", {
            "request": request, "current_user": current_user
        })
    tenant = current_user.tenant
    if not tenant:
        raise HTTPException(500, "Brak danych najemcy")
    apt = await get_apartment(db, tenant.apartment_id)
    readings = await get_readings_for_apartment(db, apt.id, limit=30)
    billing = await get_billing_periods_for_apartment(db, apt.id)
    # Get last readings per utility
    last_readings = {}
    for ut in UtilityType:
        field = ut.value
        if getattr(apt, f"has_{field}", False):
            last = await get_last_reading(db, apt.id, ut)
            last_readings[field] = last
    return templates.TemplateResponse("tenant/portal.html", {
        "request": request, "current_user": current_user,
        "tenant": tenant, "apartment": apt,
        "readings": readings, "billing_periods": billing,
        "last_readings": last_readings,
        "UTILITY_LABELS": UTILITY_LABELS,
        "today": date.today(),
    })

@router.post("/reading")
async def submit_reading(request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    utility_type: str = Form(...), reading_date: date = Form(...),
    reading_value: Decimal = Form(...), notes: str = Form(""),
    photo: UploadFile = File(None)):
    if not current_user.tenant_id:
        raise HTTPException(403)
    tenant = current_user.tenant
    apt_id = tenant.apartment_id
    photo_path = None
    if photo and photo.filename:
        os.makedirs(settings.upload_dir, exist_ok=True)
        ext = os.path.splitext(photo.filename)[1].lower()
        fname = f"{uuid.uuid4()}{ext}"
        fpath = os.path.join(settings.upload_dir, fname)
        async with aiofiles.open(fpath, "wb") as f:
            content = await photo.read()
            await f.write(content)
        photo_path = fname
    # Validate value >= previous
    last = await get_last_reading(db, apt_id, UtilityType(utility_type))
    if last and reading_value < last.reading_value:
        readings = await get_readings_for_apartment(db, apt_id, limit=30)
        billing = await get_billing_periods_for_apartment(db, apt_id)
        last_readings = {}
        apt = await get_apartment(db, apt_id)
        for ut in UtilityType:
            field = ut.value
            if getattr(apt, f"has_{field}", False):
                lr = await get_last_reading(db, apt_id, ut)
                last_readings[field] = lr
        return templates.TemplateResponse("tenant/portal.html", {
            "request": request, "current_user": current_user,
            "tenant": tenant, "apartment": apt,
            "readings": readings, "billing_periods": billing,
            "last_readings": last_readings, "UTILITY_LABELS": UTILITY_LABELS,
            "today": date.today(),
            "error": f"Odczyt nie może być mniejszy niż poprzedni ({float(last.reading_value):.3f})"
        }, status_code=422)
    await create_reading(db, apt_id, UtilityType(utility_type), reading_date,
                         reading_value, current_user.id, notes or None, photo_path)
    return RedirectResponse(url="/portal?success=1", status_code=302)
