import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# Демо-режим (True = заказы не реальные)
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("1", "true", "yes")

CURRENCY = "RUB"
CURRENCY_SYMBOL = "₽"

# Telegram Payments
# Получите provider_token у @BotFather → /mybots → Payments
# Для тестов Telegram даёт тестовый провайдер
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "")

# ЮKassa (альтернатива / дополнение)
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
