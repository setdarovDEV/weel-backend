from celery import Celery
from app.config import settings

celery_app = Celery(
    "weel_backend",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.notifications",
        "app.tasks.sms",
        "app.tasks.images",
        "app.tasks.bookings",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    worker_prefetch_multiplier=1,
)
