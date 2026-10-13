from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_reply_kb() -> ReplyKeyboardMarkup:
    """Reply-клавиатура (опционально, внизу экрана)."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🏠 Меню")
    builder.button(text="🛒 Корзина")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
