from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Uses Pydantic v2 Settings for validation and .env file support.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_name: str = "Weel API"
    debug: bool = False
    environment: str = "development"
    base_url: str = "https://dev.weel.uz/api/v2"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:3001,https://dev.weel.uz,http://dev.weel.uz"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/weel"
    sync_database_url: str = "postgresql://postgres:postgres@db:5432/weel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "change-me-please-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # MinIO / S3
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
    bot_token: str = ""
    mini_app_url: str = "https://partners.weel.uz/"

    # Admin seed
    admin_default_phone: str = "+998901234567"
    admin_default_password: str = "Weel123@#"

    # Sentry
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_origins.split(",")]
        return origins


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
