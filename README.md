# 🌷 Цветочный магазин — Telegram-бот (полный)

Полноценный бот цветочного магазина с **фото товаров**, **корзиной** и **оплатой** через Telegram Payments.

## Возможности

| Функция                        | Статус |
|--------------------------------|--------|
| Главное меню с категориями     | ✅     |
| Карточки товаров **с фото**    | ✅     |
| Пагинация (1/4, 2/4…)          | ✅     |
| Добавление в корзину           | ✅     |
| Корзина + изменение количества | ✅     |
| Оформление заказа              | ✅     |
| **Telegram Payments**          | ✅     |
| Уведомление админу             | ✅     |
| Дополнить заказ / Контакты     | ✅     |

## Быстрый старт

### 1. Создайте бота

1. Откройте [@BotFather](https://t.me/BotFather)
2. `/newbot` → имя и username
3. Скопируйте **токен**

### 2. Установите зависимости

```bash
cd flower_bot
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Настройка `.env`

```bash
cp .env.example .env
```

Заполните:

```env
BOT_TOKEN=123456:ABC-DEF...
ADMIN_IDS=ваш_telegram_id
DEMO_MODE=true
PROVIDER_TOKEN=                   # см. ниже
```

### 4. Запуск

```bash
python main.py
```

Откройте бота в Telegram → **/start**.

---

## Как включить реальную оплату

1. Напишите [@BotFather](https://t.me/BotFather)
2. `/mybots` → выберите бота → **Payments**
3. Подключите платёжную систему (ЮKassa, Stripe, Сбер и др.) или используйте **тестовый** провайдер
4. Скопируйте `provider_token` в `.env`:

```env
PROVIDER_TOKEN=ваш_provider_token
DEMO_MODE=false
```

После этого при нажатии **«Оформить заказ»** бот будет отправлять настоящий счёт Telegram.

---

## Структура проекта

```
flower_bot/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── images/                  # Фото товаров
│   ├── bouquet1.jpg
│   ├── bouquet2.jpg
│   ├── ...
├── data/
│   └── products.py          # Каталог + пути к картинкам
├── handlers/
│   ├── start.py
│   ├── catalog.py           # Категории + фото + пагинация
│   ├── cart.py              # Корзина + оплата
│   └── other.py
├── keyboards/
│   ├── inline.py
│   └── reply.py
└── utils/
    └── cart.py
```

## Как заменить картинки

1. Положите свои фото в папку `images/`
2. В `data/products.py` укажите правильные пути:

```python
"image": str(IMAGES_DIR / "my_bouquet.jpg"),
```

Поддерживаются JPG/PNG. Рекомендуемый размер — от 800×600.

## Как добавить товары

Редактируйте `data/products.py` — словари `PRODUCTS` и `CATEGORIES`.

## Важные замечания

- Корзина хранится **в памяти** (при перезапуске бота очищается). Для продакшена замените на Redis/SQLite/PostgreSQL.
- Текущие картинки — заглушки (picsum.photos). Замените на реальные фото букетов.
- Для продакшена обязательно настройте `PROVIDER_TOKEN` и `ADMIN_IDS`.

## Дальнейшее развитие

- [ ] SQLite / PostgreSQL для корзины и заказов
- [ ] Админ-панель (добавление товаров через бота)
- [ ] Загрузка фото через админку
- [ ] Выбор даты/времени доставки
- [ ] Интеграция ЮKassa напрямую

Удачных продаж! 🌷
