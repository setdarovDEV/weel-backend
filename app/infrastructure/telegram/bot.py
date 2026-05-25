import logging

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, web_app_url: str):
        self.token = token
        self.web_app_url = web_app_url
        self.application: Application | None = None

    def build(self) -> "TelegramBot":
        self.application = (
            Application.builder().token(self.token).build()
        )
        self.application.add_handler(CommandHandler("start", self._start_command))
        return self

    async def _start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        keyboard = [
            [InlineKeyboardButton("🚀 Dasturni ochish", url=self.web_app_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Weel bot ishga tushdi! Quyidagi tugma orqali ilovani oching 👇",
            reply_markup=reply_markup,
        )

    async def _set_menu_button(self) -> None:
        try:
            bot = self.application.bot
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="weel.uz",
                    web_app=WebAppInfo(url=self.web_app_url),
                )
            )
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Botni ishga tushurish ♻"),
                ]
            )
        except Exception as e:
            logger.warning(f"Failed to set menu button: {e}")

    async def start(self) -> None:
        await self.application.initialize()
        await self.application.start()
        await self._set_menu_button()
        await self.application.updater.start_polling()
        logger.info("Telegram bot polling started")

    async def stop(self) -> None:
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram bot stopped")

    async def send_message(self, chat_id: int, text: str) -> None:
        await self.application.bot.send_message(chat_id=chat_id, text=text)
