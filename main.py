"""
Цветочный магазин — Telegram-бот (демо)
Запуск: python main.py
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import setup_routers
from data.database import init_db


async def main():
    # Инициализируем базу данных
    await init_db()

    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не задан!")
        print("Создайте файл .env и добавьте строку:")
        print("BOT_TOKEN=ваш_токен_от_BotFather")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем все роутеры
    root_router = setup_routers()
    dp.include_router(root_router)

    # Удаляем вебхук (если был) и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)

    print("🌷 Бот цветочного магазина запущен!")
    print("Нажмите Ctrl+C для остановки")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())