from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.auth.security import decode_token

async def get_current_user_optional(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == int(user_id), User.is_active == True))
    return result.scalar_one_or_none()

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user = await get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user

async def require_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user = await get_current_user(request, db)
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Brak uprawnień administratora")
    return user

async def get_current_user_redirect(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user = await get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return user
