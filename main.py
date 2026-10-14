"""
Цветочный магазин — Telegram-бот
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import BOT_TOKEN
from handlers import setup_routers
from data.database import (
    init_db, migrate_db, migrate_important_dates,
    save_client, count_products, add_product,
)
from data.products import PRODUCTS as OLD_PRODUCTS


class ClientMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.from_user:
            await save_client(
                event.from_user.id,
                event.from_user.username or "",
                event.from_user.full_name,
            )
        return await handler(event, data)


async def main():
    await init_db()
    await migrate_db()
    await migrate_important_dates()

    if await count_products() == 0:
        for category, items in OLD_PRODUCTS.items():
            for item in items:
                await add_product(
                    category=category,
                    name=item["name"],
                    price=item["price"],
                    description=item["description"],
                    image=item.get("image"),
                )
        print("✅ Товары загружены в базу данных")

    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не задан!")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ClientMiddleware())

    root_router = setup_routers()
    dp.include_router(root_router)

    await bot.delete_webhook(drop_pending_updates=True)
    print("🌷 Бот цветочного магазина запущен!")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())