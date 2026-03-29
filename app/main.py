from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.database import engine, get_db
from app.models import Base
from app.models.user import UserRole
from app.config import get_settings
from app.routers import auth, admin, apartments, rates, meters, billing_router, portal
from app.crud.users import get_user_by_email, create_admin_user
from sqlalchemy.ext.asyncio import AsyncSession
import os
from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Create default admin if not exists
    async with AsyncSession(engine) as db:
        admin_user = await get_user_by_email(db, "admin@rental.local")
        if not admin_user:
            await create_admin_user(db, "admin@rental.local", "admin123")
            await db.commit()
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

class NgrokSkipWarningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response

app.add_middleware(NgrokSkipWarningMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(apartments.router)
app.include_router(rates.router)
app.include_router(meters.router)
app.include_router(billing_router.router)
app.include_router(portal.router)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login", status_code=302)
