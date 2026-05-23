from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/notify", status_code=200)
async def notify(request: Request, telegram_id: int, text: str):
    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")

    bot = request.app.state.telegram_bot
    if bot is None:
        raise HTTPException(status_code=503, detail="Telegram bot not running")

    await bot.send_message(chat_id=telegram_id, text=text)
    return {"status": "sent", "telegram_id": telegram_id}
