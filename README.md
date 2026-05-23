# Weel Backend - Professional FastAPI

Weel booking platformining professional FastAPI backend'i. **SOLID** prinsiplari, **Clean Architecture** va **5NF** normalizatsiyaga asoslangan.

## Arxitektura

```
app/
├── core/                    # Konfiguratsiya, xavfsizlik, logging, constants
├── domain/                  # Biznes qoidalar va abstract interfeyslar (ports)
│   ├── entities/
│   └── repositories/        # IRepository, IUnitOfWork (Protocol)
├── infrastructure/          # Texnik implementatsiyalar (adapters)
│   ├── database/
│   │   ├── connection.py    # SQLAlchemy 2.0 async engine + session
│   │   └── models/          # 5NF ORM modellari
│   ├── repositories/        # SqlAlchemyRepository (generic)
│   ├── external/            # MinIO, SMS, Payment, Firebase
│   ├── cache/               # Redis wrapper
│   └── unit_of_work.py      # Transaction boundary
├── application/             # Use case'lar (services)
│   ├── dto/                 # Data Transfer Objects (Pydantic)
│   └── services/            # AuthService, PropertyService, BookingService...
└── presentation/            # FastAPI + WebSocket
    └── api/v1/
        ├── deps.py          # Dependency injection
        ├── schemas/         # Request/Response modellari
        └── routers/         # Endpoint'lar
```

## SOLID Prinsiplari

- **S (SRP)**: Har bir service, repository va router faqat bitta vazifani bajaradi.
- **O (OCP)**: `SqlAlchemyRepository` generic klassi orqali yangi entity'lar kengaytiriladi, eski kod o'zgartirilmaydi.
- **L (LSP)**: Repository implementatsiyalari abstract interfeysni to'liq qondiradi.
- **I (ISP)**: Kichik, maqsadli interfeyslar (`IRepository`, `IUnitOfWork`).
- **D (DIP)**: Application layer faqat abstract repository'larga bog'liq. Concrete implementation'lar FastAPI `Depends` orqali inject qilinadi.

## Ma'lumotlar bazasi (PostgreSQL 5NF)

Barcha jadvallar **5-Normal Form** (5NF) bo'yicha normalizatsiya qilingan:

- **users** – atomik foydalanuvchi ma'lumotlari
- **user_roles** – M2M junction, rollarni alohida faktlar sifatida ajratish
- **clients / partners / admins** – role-specific attribute'lar (1:1, subtype pattern)
- **properties** – barcha property detail'lari bitta jadvalda (join dependency yo'q)
- **property_services + property_service_links** – xizmatlar va ular orasidagi aloqa
- **property_prices** – vaqtga bog'liq narxlar (shartli faktlar)
- **bookings** – booking va uning narx ma'lumotlari bitta jadvalda (1:1 join dependency olib tashlangan)
- **calendar_dates** – kunlik bandlik/erkinlik faktlari
- **locations** – o'z-o'ziga murojaat qiluvchi ierarxik jadval (region -> district -> prefecture)
- **translations** – umumiy tarjima jadvali (entity_type, entity_id, field_name, lang_code) – multi-language faktlarni to'liq normalizatsiya qiladi

## Boshlash

```bash
cp .env.example .env
# .env faylini tahrirlang
docker-compose up --build
```

## API Versiyalari

- **v2 (new)**: `/api/v1/...` – Clean Architecture, SOLID, professionallik.
- **v1 (legacy)**: `/api/...` – Eski endpoint'lar (backward compatibility).

Migatsiya:
- Frontend va mobile dasturlar `/api/v1/...` ga o'tishlari mumkin.
- Eski `/api/...` endpoint'lar hali ham ishlaydi.

## Migration'lar

```bash
# Yangi migration yaratish
alembic revision --autogenerate -m "description"

# Qo'llash
alembic upgrade head
```

## Test

```bash
pytest
```

## Texnologiyalar

- **FastAPI** 0.115+ (async)
- **SQLAlchemy** 2.0 + asyncpg (PostgreSQL)
- **Pydantic** v2 (validation + settings)
- **Alembic** (migrations)
- **Redis** + Celery (background tasks)
- **MinIO** (S3-compatible storage)
- **Firebase Admin** (push notifications)
- **Sentry** (error tracking)
- **python-jose** + **passlib** (JWT + bcrypt)
