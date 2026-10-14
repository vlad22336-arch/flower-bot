from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup

from config import ADMIN_IDS
from data.database import save_client


router = Router()


# ===== КЛАВИАТУРА ГЛАВНОГО МЕНЮ =====

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню клиента (внизу экрана)."""
    b = ReplyKeyboardBuilder()
    b.button(text="💐 Букеты")
    b.button(text="🎁 Цветы в коробке")
    b.button(text="🪴 Растения")
    b.button(text="✨ Дополнить заказ")
    b.button(text="🛒 Корзина")
    b.button(text="🎂 Важные даты")
    b.button(text="💬 Менеджер")
    b.button(text="📍 Контакты")
    b.adjust(2, 2, 2, 2)
    return b.as_markup(resize_keyboard=True)


# ===== ГЛАВНАЯ СТРАНИЦА /start =====

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user

    # Сохраняем клиента в базу
    try:
        await save_client(user.id, user.username or "", user.full_name)
    except Exception:
        pass

    text = (
        f"👋 <b>Здравствуйте, {user.first_name}!</b>\n\n"
        "🌷 Добро пожаловать в <b>«Цветочную лавку Орхидея»</b>!\n\n"
        "Свежие цветы и авторские букеты, собранные в день заказа.\n\n"
        "🌿 <b>Что мы предлагаем:</b>\n"
        "• 💐 Авторские букеты\n"
        "• 🎁 Цветы в коробке\n"
        "• 🪴 Комнатные растения\n"
        "• ✨ Дополнительные подарки\n\n"
        "🚚 <b>Доставка:</b>\n"
        "• По городу — от 300 ₽\n"
        "• Срочная доставка — от 500 ₽\n"
        "• Самовывоз — бесплатно\n\n"
        "🕒 <b>Режим работы:</b> 9:00 – 21:00\n\n"
        "👇 Выберите раздел в меню ниже, чтобы начать."
    )

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


# ===== О НАС / О МАГАЗИНЕ =====

@router.message(F.text == "📍 Контакты")
@router.message(Command("about"))
async def cmd_about(message: Message):
    text = (
        "🌷 <b>О магазине «Цветочная лавка Орхидея»</b>\n\n"
        "Мы — небольшая мастерская, где каждый букет собирается вручную из свежих цветов.\n\n"
        "📍 <b>Адрес:</b>\n"
        "г. Москва, ул. Цветочная, 15\n\n"
        "📞 <b>Телефон:</b>\n"
        "+7 (999) 123-45-67\n\n"
        "📧 <b>Email:</b>\n"
        "flowers@example.com\n\n"
        "🕒 <b>Режим работы:</b>\n"
        "Ежедневно 9:00 – 21:00\n\n"
        "🚚 <b>Доставка:</b>\n"
        "• По городу — от 300 ₽\n"
        "• Срочная доставка — от 500 ₽\n"
        "• Самовывоз — бесплатно"
    )
    await message.answer(text, parse_mode="HTML")


# ===== СВЯЗАТЬСЯ С МЕНЕДЖЕРОМ =====

@router.message(F.text == "💬 Менеджер")
async def cmd_manager(message: Message):
    text = (
        "💬 <b>Связь с менеджером</b>\n\n"
        "Напишите ваш вопрос прямо в этот чат — "
        "менеджер ответит в ближайшее время.\n\n"
        "Или позвоните: +7 (999) 123-45-67\n\n"
        "🕒 Мы работаем ежедневно с 9:00 до 21:00."
    )
    await message.answer(text, parse_mode="HTML")


# ===== ПОМОЩЬ (скрытая админ-команда) =====

@router.message(Command("help"))
async def cmd_help(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS

    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "🌷 <b>Для клиентов:</b>\n"
        "• <b>💐 Букеты</b> — каталог букетов\n"
        "• <b>🎁 Цветы в коробке</b> — композиции в коробках\n"
        "• <b>🪴 Растения</b> — комнатные растения\n"
        "• <b>✨ Дополнить заказ</b> — открытки, шары, шоколад\n"
        "• <b>🛒 Корзина</b> — оформить заказ\n"
        "• <b>🎂 Важные даты</b> — напоминания\n"
        "• <b>💬 Менеджер</b> — связаться с нами\n"
        "• <b>📍 Контакты</b> — адрес и телефон\n"
    )

    if is_admin:
        text += (
            "\n👑 <b>Для админа:</b>\n"
            "• /admin — админ-панель\n"
            "• /help — эта справка"
        )

    await message.answer(text, parse_mode="HTML")


# ===== ВОЗВРАТ В МЕНЮ =====

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🌷 <b>Главное меню</b>\n\nВыберите раздел:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()