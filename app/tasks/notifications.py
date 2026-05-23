import httpx
from app.config import settings
from app.tasks.celery_app import celery_app

NOTIFY_URL = settings.base_url.rstrip("/") + "/telegram/notify"


@celery_app.task(bind=True, max_retries=3)
def send_telegram_notification(self, telegram_id: int, text: str):
    """Send notification through the FastAPI Telegram bot endpoint."""
    try:
        response = httpx.post(
            NOTIFY_URL,
            params={"telegram_id": telegram_id, "text": text},
            timeout=10.0,
        )
        response.raise_for_status()
        return {"status": "sent", "telegram_id": telegram_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
