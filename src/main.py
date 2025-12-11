from aiogram import Dispatcher, Bot
from dotenv import load_dotenv
import os
from src.app.handlers.handlers import router
import logging

load_dotenv()

logger = logging.getLogger(__name__)


async def main():
    BOT_TOKEN = os.getenv("TOKEN")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)
    logger.info("Функция запуска бота в main.py вызвана.")
    await dp.start_polling(bot)





