from fastapi import APIRouter, Depends, Request, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.dependencies import require_admin, get_current_user
from app.models.user import User, UserRole
from app.models.utility_rate import UtilityType
from app.models.meter_reading import MeterReading
from sqlalchemy import select, update
from app.crud.apartments import get_apartment
from app.crud.meter_readings import create_reading, get_last_reading
from app.config import get_settings
from datetime import date
from decimal import Decimal
import os, aiofiles, uuid

router = APIRouter(prefix="/admin/meters")
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()

UTILITY_LABELS = {
    "water": "Woda", "electricity": "Prąd",
    "gas": "Gaz", "trash": "Śmieci", "heating": "Ogrzewanie"
}

@router.post("/{apt_id}/add")
async def add_reading(apt_id: int, request: Request, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    utility_type: str = Form(...), reading_date: date = Form(...),
    reading_value: Decimal = Form(...), notes: str = Form("")):
    apt = await get_apartment(db, apt_id)
    if not apt:
        raise HTTPException(404)
    await create_reading(db, apt_id, UtilityType(utility_type), reading_date,
                         reading_value, current_user.id, notes or None)
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)

@router.post("/{reading_id}/verify-photo")
async def verify_photo(reading_id: int, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(require_admin)):
    from datetime import datetime, timezone
    result = await db.execute(select(MeterReading).where(MeterReading.id == reading_id))
    reading = result.scalar_one_or_none()
    if reading:
        reading.photo_verified = True
        reading.photo_verified_by_id = current_user.id
        reading.photo_verified_at = datetime.now(timezone.utc)
    apt_id = reading.apartment_id if reading else 0
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)

@router.post("/{reading_id}/edit")
async def edit_reading(reading_id: int, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    reading_date: date = Form(...), reading_value: Decimal = Form(...),
    notes: str = Form("")):
    result = await db.execute(select(MeterReading).where(MeterReading.id == reading_id))
    reading = result.scalar_one_or_none()
    if not reading:
        raise HTTPException(404)
    reading.reading_date = reading_date
    reading.reading_value = reading_value
    reading.notes = notes or None
    # Recalculate consumption vs previous reading
    if reading.previous_reading_id:
        prev_res = await db.execute(select(MeterReading).where(MeterReading.id == reading.previous_reading_id))
        prev = prev_res.scalar_one_or_none()
        if prev:
            reading.consumption = reading_value - prev.reading_value
    apt_id = reading.apartment_id
    await db.flush()
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)


@router.post("/{reading_id}/delete")
async def delete_reading(reading_id: int, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(require_admin)):
    from app.models.billing import BillingItem
    from sqlalchemy import update as sql_update
    result = await db.execute(select(MeterReading).where(MeterReading.id == reading_id))
    reading = result.scalar_one_or_none()
    if not reading:
        raise HTTPException(404)
    apt_id = reading.apartment_id
    # Unlink from billing_items before deleting
    await db.execute(
        sql_update(BillingItem)
        .where((BillingItem.reading_to_id == reading_id) | (BillingItem.reading_from_id == reading_id))
        .values(reading_to_id=None, reading_from_id=None)
    )
    await db.delete(reading)
    await db.flush()
    return RedirectResponse(url=f"/admin/apartments/{apt_id}", status_code=302)
