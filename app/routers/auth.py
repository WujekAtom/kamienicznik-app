from fastapi import APIRouter, Depends, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud.users import get_user_by_email, get_user_by_magic_token
from app.auth.security import verify_password, create_access_token
from app.auth.dependencies import get_current_user_optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models.user import User
from app.crud.users import get_user_by_email, get_user_by_magic_token, get_user_by_reset_token
from app.auth.security import verify_password, create_access_token, hash_password, generate_reset_token
from fastapi import BackgroundTasks
from app.email import send_reset_email

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

RESET_TOKEN_TTL_MIN = 60  # ważność linku resetującego w minutach

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_optional(request, db)
    if user:
        if user.role.value == "admin":
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/portal", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, response: Response,
                       email: str = Form(...), password: str = Form(...),
                       db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Nieprawidłowy email lub hasło"
        }, status_code=401)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    redirect_url = "/admin" if user.role.value == "admin" else "/portal"
    resp = RedirectResponse(url=redirect_url, status_code=302)
    resp.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=60*60*24*7)
    return resp

@router.get("/magic/{token}", response_class=HTMLResponse)
async def magic_link_login(token: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_magic_token(db, token)
    if not user:
        return RedirectResponse(url="/login?error=invalid_link", status_code=302)
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    resp = RedirectResponse(url="/portal", status_code=302)
    resp.set_cookie("access_token", access_token, httponly=True, samesite="lax", max_age=60*60*24*7)
    return resp

@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {
        "request": request,
        "message": None,
        "token": None,
    })

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, email)

    if user and user.is_active:
        token = generate_reset_token()
        user.reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MIN)
        await db.commit()

        reset_link = f"{request.base_url}reset-password?token={token}"
        background_tasks.add_task(send_reset_email, user.email, reset_link)

    message = "Jeśli podany email istnieje w systemie, wysłaliśmy link do resetu hasła."

    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "message": message,
            "token": None,
        },
    )

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_reset_token(db, token)
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.now(timezone.utc):
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "token": token,
            "error": "Link resetujący jest nieprawidłowy lub wygasł.",
        }, status_code=400)

    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "token": token,
        "error": None,
    })


@router.post("/reset-password")
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(..., min_length=8, max_length=72),
    db: AsyncSession = Depends(get_db),
):

    # walidacja na poziomie bajtów (ważne przy polskich znakach)
    if len(password.encode("utf-8")) > 72:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Hasło może mieć maksymalnie 72 bajty (bez bardzo długich znaków specjalnych).",
            },
            status_code=400,
        )

    user = await get_user_by_reset_token(db, token)
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.now(timezone.utc):
        return templates.TemplateResponse("reset_password.html", {
            "request": Request,  # jeśli chcesz użyć Request, musisz dodać go jako parametr
            "token": token,
            "error": "Link resetujący jest nieprawidłowy lub wygasł.",
        }, status_code=400)

    user.hashed_password = hash_password(password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()

    return RedirectResponse(url="/login", status_code=302)