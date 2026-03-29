# Aplikacja do Zarządzania Najmem

## Uruchomienie lokalne (Docker)

```bash
cp .env.example .env
# Edytuj .env - ustaw haslo bazy danych i SECRET_KEY
docker compose up --build
```

Aplikacja dostepna: http://localhost:8000

**Admin:** admin@rental.local / admin123  (zmien po pierwszym logowaniu!)

## Endpointy

- `/login` - logowanie
- `/admin` - panel administratora  
- `/admin/apartments` - lokale
- `/admin/rates` - stawki mediow
- `/admin/billing/list` - rozliczenia
- `/portal` - panel najemcy
- `/magic/{token}` - logowanie przez link

## Deployment produkcyjny (Hetzner CX22, ~4 EUR/mies.)

```bash
apt update && apt install -y docker.io docker-compose-v2
git clone <repo> && cd rental-app
cp .env.example .env
# Edytuj .env i nginx.conf (zamien YOUR_DOMAIN.COM)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Zmiana hasla admina

```bash
docker compose exec web python3 << 'EOF'
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine
from app.crud.users import get_user_by_email
from app.auth.security import hash_password

async def run():
    async with AsyncSession(engine) as db:
        user = await get_user_by_email(db, "admin@rental.local")
        user.hashed_password = hash_password("NOWE_SILNE_HASLO")
        await db.commit()
        print("Haslo zmienione!")
asyncio.run(run())
EOF
```

## v2 - planowane funkcje

- Upload zdjecia licznika (pole photo_path juz w modelu)
- Weryfikacja zdjec przez admina (pole photo_verified juz w modelu)
- Powiadomienia email (SMTP)
- Eksport PDF rozliczen
