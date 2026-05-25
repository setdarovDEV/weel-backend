import os
import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    DomainException,
    NotFoundException,
    PaymentException,
    ValidationException,
)
from app.core.logging_config import configure_logging
from app.presentation.api.v1.routers import auth, telegram, users
from app.routers import properties

logger = logging.getLogger(__name__)

# Configure logging at startup
configure_logging()

# Initialize Sentry if DSN is provided
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (idempotent - safe for existing databases)
    try:
        from app.infrastructure.database.connection import create_engine, Base
        async with create_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")
    except Exception as e:
        logger.warning(f"Could not ensure database tables: {e}")

    if settings.bot_token:
        from app.infrastructure.telegram.bot import TelegramBot

        bot = TelegramBot(
            token=settings.bot_token,
            web_app_url=settings.mini_app_url,
        )
        bot.build()
        await bot.start()
        app.state.telegram_bot = bot
        logger.info("Telegram bot started successfully")
    else:
        app.state.telegram_bot = None
        logger.warning("BOT_TOKEN not set; Telegram bot not started")

    yield

    if app.state.telegram_bot:
        await app.state.telegram_bot.stop()
        logger.info("Telegram bot stopped")


app = FastAPI(
    title=settings.app_name,
    description="Weel Booking Platform API - Professional FastAPI Backend",
    version="2.0.0",
    docs_url="/api/v2/docs" if settings.debug else None,
    redoc_url="/api/v2/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Static files (icons)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount(
        "/icons", StaticFiles(directory=os.path.join(static_dir, "icons")), name="icons"
    )


# Global exception handler: Domain exceptions -> HTTP responses
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    status_map = {
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "VALIDATION_ERROR": 422,
        "AUTHENTICATION_ERROR": 401,
        "AUTHORIZATION_ERROR": 403,
        "PAYMENT_ERROR": 402,
        "EXTERNAL_SERVICE_ERROR": 502,
    }
    status_code = status_map.get(exc.code, 500)
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
    )


# Catch-all exception handler to ensure CORS headers on unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# Health check
@app.get("/api/v2/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "2.0.0", "architecture": "clean"}


# API v1 Routers (new clean architecture endpoints)
app.include_router(auth.router, prefix="/api/v2/user", tags=["Auth"])
app.include_router(users.router, prefix="/api/v2/user", tags=["Users"])
app.include_router(telegram.router, prefix="/api/v2/telegram", tags=["Telegram"])
app.include_router(properties.router, prefix="/api/v2/property", tags=["Properties"])

# Legacy API v1 (backward compatibility) - import old routers if still present
# This bridges old mobile/frontends until they migrate to /api/v1/ paths
try:
    from app.routers import admin
    from app.routers.admin import property_admin_router, booking_admin_router, story_admin_router, services_router
    from app.routers.chat import router as chat_router
    from app.websocket.chat_ws import router as ws_router

    app.include_router(admin.router, prefix="/api/v2/admin", tags=["Admin (Legacy)"])
    app.include_router(admin.router, prefix="/api/v2/admin-auth", tags=["Admin Auth"])
    app.include_router(property_admin_router, prefix="/api/v2/property/admin", tags=["Property Admin"])
    app.include_router(booking_admin_router, prefix="/api/v2/booking/admin", tags=["Booking Admin"])
    app.include_router(story_admin_router, prefix="/api/v2/story/admin", tags=["Story Admin"])
    app.include_router(services_router, prefix="/api/v2/property/services", tags=["Property Services"])
    app.include_router(chat_router, prefix="/api/v2/chat", tags=["Chat"])
    app.include_router(ws_router, prefix="/api/v2/ws")
except ImportError as e:
    import logging

    logging.getLogger(__name__).warning(f"Legacy routers not fully loaded: {e}")
