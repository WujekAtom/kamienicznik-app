from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.user import User
from app.models.apartment import Apartment
from app.models.billing import BillingPeriod, BillingStatus
from app.models.payment import Payment
from app.models.meter_reading import MeterReading
from app.crud.apartments import get_apartments
from app.crud.payments import get_recent_payments
from datetime import date

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_admin)):
    apartments = await get_apartments(db)
    overdue_count_res = await db.execute(
        select(func.count(BillingPeriod.id)).where(BillingPeriod.status == BillingStatus.overdue)
    )
    overdue_count = overdue_count_res.scalar() or 0
    recent_payments = await get_recent_payments(db, limit=5)
    pending_photos_res = await db.execute(
        select(func.count(MeterReading.id)).where(
            MeterReading.photo_path != None,
            MeterReading.photo_verified == False
        )
    )
    pending_photos = pending_photos_res.scalar() or 0
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "apartments": apartments,
        "overdue_count": overdue_count,
        "recent_payments": recent_payments,
        "pending_photos": pending_photos,
        "today": date.today(),
    })
