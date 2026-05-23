from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    app_name: str = "Weel API"
    debug: bool = False
    environment: str = "development"
    base_url: str = "https://dev.weel.uz/api"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/weel"
    sync_database_url: str = "postgresql://postgres:postgres@db:5432/weel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "weel-uploads"
    minio_secure: bool = False

    # Eskiz SMS
    eskiz_email: str = ""
    eskiz_password: str = ""
    eskiz_base_url: str = "https://notify.eskiz.uz/api"

    # Plum Payment
    plum_base_url: str = ""
    plum_api_key: str = ""
    plum_secret: str = ""

    # Firebase
    firebase_credentials_path: str = "/app/firebase-credentials.json"

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_bot_notify_url: str = "http://weel-bot:8002/api/notify/"
    telegram_bot_secret: str = ""

    # Admin
    admin_default_phone: str = "+998901234567"
    admin_default_password: str = "Weel123@#"

    # Sentry
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
