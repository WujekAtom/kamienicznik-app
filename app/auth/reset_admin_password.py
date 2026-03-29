import asyncio
from getpass import getpass

from sqlalchemy import select
from app.database import get_db, async_sessionmaker  # albo get_db, jeśli tak masz
from app.models.user import User
from app.auth.security import hash_password  # funkcja, której używasz przy rejestracji

ADMIN_EMAIL = "admin@rental.local"


async def main():
    new_password = getpass("Nowe hasło dla admin@rental.local: ")

    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        admin = result.scalar_one_or_none()

        if not admin:
            print(f"Użytkownik {ADMIN_EMAIL} nie istnieje, tworzę nowego admina...")
            admin = User(
                email=ADMIN_EMAIL,
                full_name="Administrator",
                is_active=True,
                is_superuser=True,
                hashed_password=hash_password(new_password),
            )
            db.add(admin)
        else:
            print(f"Zmieniam hasło dla {ADMIN_EMAIL}...")
            admin.hashed_password = hash_password(new_password)

        await db.commit()
        print("Gotowe.")


if __name__ == "__main__":
    asyncio.run(main())